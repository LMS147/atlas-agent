"""Install/control Atlas under Termux's runit supervisor; never copy secrets into service files."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time

from backend.app.config import load_settings
from backend.healthcheck import probe

SERVICE = "atlas-api"
ROOT = Path(__file__).resolve().parents[1]
MARKER = "atlas-managed.json"


def _write(path, content, mode=0o700):
    temporary = path.with_name(path.name + ".atlas-new")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(mode)
    temporary.replace(path)


def install_service(root: Path, prefix: Path, python: str, boot_dir: Path | None = None):
    root = root.resolve()
    prefix = prefix.resolve()
    shell = prefix / "bin" / "sh"
    for name in ("sh", "sv", "svlogd", "runsvdir"):
        if not (prefix / "bin" / name).is_file():
            raise RuntimeError("Install termux-services first, then restart your Termux shell")
    executable = os.path.abspath(shutil.which(python) or python)  # Preserve a virtualenv's symlink path.
    if not Path(executable).is_file():
        raise RuntimeError("The configured Python executable does not exist")
    service = prefix / "var" / "service" / SERVICE
    log_dir = prefix / "var" / "log" / "sv" / SERVICE
    marker = service / MARKER
    if service.exists() and not marker.exists():
        raise RuntimeError("An unmanaged atlas-api service already exists; it will not be overwritten")
    if marker.exists() and json.loads(marker.read_text())["root"] != str(root):
        raise RuntimeError("atlas-api belongs to another checkout; stop/uninstall it there first")
    service.mkdir(parents=True, exist_ok=True)
    (service / "log").mkdir(exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    first_install = not marker.exists()
    if first_install:
        (service / "down").touch()  # Configure first; enabling is a separate, explicit operation.
    q = shlex.quote
    _write(service / "run", f"#!{shell}\nexec 2>&1\ncd {q(str(root))}\nexec {q(executable)} -m backend.app\n")
    _write(service / "finish", f'#!{shell}\nif [ "${{1:-0}}" != 0 ] || [ "${{2:-0}}" != 0 ]; then sleep 5; fi\n')
    _write(service / "log" / "run", f"#!{shell}\nexec {q(str(prefix / 'bin' / 'svlogd'))} -tt {q(str(log_dir))}\n")
    _write(log_dir / "config", "s1048576\nn5\n", 0o600)
    data = {"root": str(root), "python": executable, "service": SERVICE}
    _write(marker, json.dumps(data) + "\n", 0o600)
    if boot_dir is not None:
        boot_dir.mkdir(parents=True, exist_ok=True)
        boot = boot_dir / "50-atlas-api"
        if boot.exists() and "# Atlas managed boot" not in boot.read_text():
            raise RuntimeError("An unmanaged 50-atlas-api boot script exists; it will not be overwritten")
        _write(boot, f"#!{shell}\n# Atlas managed boot\nexport PREFIX={q(str(prefix))}\nexport SVDIR={q(str(prefix / 'var' / 'service'))}\nexport LOGDIR={q(str(prefix / 'var' / 'log'))}\nif [ ! -e {q(str(service / 'down'))} ]; then {q(str(prefix / 'bin' / 'termux-wake-lock'))} >/dev/null 2>&1 || true; fi\n{q(str(prefix / 'bin' / 'service-daemon'))} start >/dev/null 2>&1 || true\n")
    return service


def _prefix():
    value = os.getenv("PREFIX")
    if not value:
        raise RuntimeError("Run this command inside Termux with termux-services installed")
    return Path(value)


def _service(prefix):
    path = prefix / "var" / "service" / SERVICE
    marker = path / MARKER
    if not marker.is_file() or json.loads(marker.read_text())["root"] != str(ROOT):
        raise RuntimeError("Install the managed Atlas service from this checkout first")
    return path


def _environment(prefix):
    return {**os.environ, "SVDIR": str(prefix / "var" / "service"), "LOGDIR": str(prefix / "var" / "log")}


def _daemon(prefix):
    daemon = prefix / "bin" / "service-daemon"
    if daemon.exists():
        subprocess.run([str(daemon), "start"], env=_environment(prefix), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def _wait_supervisor(service):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if (service / "supervise" / "ok").exists():
            return
        time.sleep(0.1)
    raise RuntimeError("Termux service-daemon is not supervising Atlas yet; restart your Termux shell")


def _pid(service):
    try:
        pid = int((service / "supervise" / "pid").read_text().strip())
        return pid if pid > 0 else None
    except (OSError, ValueError):
        return None


def control(action, prefix):
    service = _service(prefix)
    if action == "logs":
        log = prefix / "var" / "log" / "sv" / SERVICE / "current"
        if log.exists():
            print("\n".join(log.read_text(errors="replace").splitlines()[-100:]))
        else:
            print("No service log yet")
        return 0
    if action == "health":
        pid = _pid(service)
        healthy, _ = probe(expected_pid=pid) if pid else (False, None)
        print("Atlas service is healthy" if healthy else "Atlas service is stopped, starting, or unhealthy")
        return 0 if healthy else 1
    if action in ("start", "enable", "restart"):
        config = load_settings()
        if not _pid(service):
            try:
                host = {"0.0.0.0":"127.0.0.1","::":"::1"}.get(config.host,config.host)
                with socket.create_connection((host,config.port),timeout=0.3):
                    raise RuntimeError("The API port is occupied by another process. Stop the manual API first")
            except OSError:
                pass
        load_settings()  # Validate without printing or copying credentials.
        if action == "enable":
            (service / "down").unlink(missing_ok=True)
        _daemon(prefix)
        _wait_supervisor(service)
    if action == "disable":
        (service / "down").touch()
    command = {"start": "up", "enable": "up", "stop": "down", "disable": "down", "restart": "restart", "status": "status"}[action]
    result = subprocess.run([str(prefix / "bin" / "sv"), "-w", "30", command, str(service)], env=_environment(prefix), check=False)
    if result.returncode:
        return result.returncode
    if action == "status":
        return control("health", prefix)
    if action in ("start","enable","restart"):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            pid = _pid(service)
            healthy, _ = probe(expected_pid=pid) if pid else (False,None)
            if healthy:
                wake = prefix / "bin" / "termux-wake-lock"
                if wake.exists():
                    subprocess.run([str(wake)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
                print("Atlas service is ready; authenticated health matches the supervised process")
                return 0
            time.sleep(0.25)
        print("Service is not ready yet; inspect service.sh logs and service.sh status",file=sys.stderr)
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Atlas Termux API service")
    parser.add_argument("action", choices=["install", "start", "stop", "restart", "enable", "disable", "status", "health", "logs"])
    parser.add_argument("--boot", action="store_true", help="Install an Atlas-only Termux:Boot hook")
    parser.add_argument("--enable", action="store_true", help="Enable/start after installation")
    args = parser.parse_args(argv)
    try:
        prefix = _prefix()
        if args.action == "install":
            # An older, unsupervised API must be stopped before changing startup ownership.
            config = load_settings()
            try:
                host = {"0.0.0.0": "127.0.0.1", "::": "::1"}.get(config.host, config.host)
                with socket.create_connection((host, config.port), timeout=0.3):
                    occupied = True
            except OSError:
                occupied = False
            target = prefix / "var" / "service" / SERVICE
            if occupied and not _pid(target):
                raise RuntimeError("An API already uses this port. Stop the manual API before installing the service")
            service = install_service(ROOT, prefix, os.getenv("ATLAS_PYTHON", sys.executable), Path.home() / ".termux" / "boot" if args.boot else None)
            print(f"Atlas service configured at {service}")
            if args.enable:
                return control("enable", prefix)
            print("Enable it with: bash deployment/termux/service.sh enable")
            return 0
        return control(args.action, prefix)
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
