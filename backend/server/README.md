# Phone server code

The host scripts below are based on the uploaded **How to create a server using a
phone (3)** guide. They manage SSH and the Cloudflare connector independently of
the Atlas AI application.

| Repository source | Installed phone location | Purpose |
|---|---|---|
| `termux/start.sh` | `~/start.sh` | Acquire a wake lock, start SSH if needed, request tunnel startup |
| `termux/tunnel.sh` | `~/tunnel.sh` | Run one connector and retry 10 seconds after it exits |
| `termux/boot/00-start-server` | `~/.termux/boot/00-start-server` | Launch the host startup script after boot |
| Private file, never committed | `~/token.txt` | Existing Cloudflare tunnel token |
| `termux_service.py` | Run from this checkout | Install/control the separate Atlas API service |
| `healthcheck.py` | Run from this checkout | Verify the separate Atlas API |

The source guide's spaced `- -` flags and smart quotes are corrected. These scripts
use Bash explicitly, per-user file locks for duplicate launch prevention, and
Cloudflare's `--token-file` option so the token is not placed in command arguments.
They create private logs under `~/server/logs`. Log rotation is not included.

## Prepare the phone

```sh
pkg install openssh cloudflared procps util-linux -y
cloudflared --version
```

`--token-file` requires cloudflared 2025.4.0 or later. Install Termux:Boot from the
same source as Termux, open it once, and allow unrestricted battery use for both.
Keep Tailscale connected for the independent SSH recovery path.

Create or keep the existing private token file on the phone:

```sh
nano ~/token.txt
chmod 600 ~/token.txt
```

Store only the tunnel token in that file. The repository contains no real token.

## Review existing startup ownership first

Your phone currently runs SSH and cloudflared outside their disabled runit services.
Keep one owner for each service. These templates preserve the home-script approach
from the guide. Do not also enable the runit `cloudflared` or `sshd` service while
using it. The templates refuse to duplicate a currently running connector.

Inspect existing `~/.termux/boot/start-all` and other personal boot scripts privately.
Disable the SSH/tunnel startup lines that duplicate `00-start-server`, preserving
unrelated work. Back up an obsolete boot script outside `~/.termux/boot` before
removing it from that directory. Merely renaming it inside the boot directory is
insufficient because Termux:Boot may execute it again.

## Copy the templates after reviewing the differences

From the repository root, first back up the existing home scripts:

```sh
backup_dir="$HOME/server/backups/host-scripts-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup_dir" "$HOME/.termux/boot"
for file in "$HOME/start.sh" "$HOME/tunnel.sh" "$HOME/.termux/boot/00-start-server"; do
    if [ -f "$file" ]; then cp -p "$file" "$backup_dir/"; fi
done
cp backend/server/termux/start.sh "$HOME/start.sh"
cp backend/server/termux/tunnel.sh "$HOME/tunnel.sh"
cp backend/server/termux/boot/00-start-server "$HOME/.termux/boot/00-start-server"
chmod 700 "$HOME/start.sh" "$HOME/tunnel.sh" "$HOME/.termux/boot/00-start-server"
```

Copying files does not replace already running processes. On the next clean boot,
the boot script uses the installed templates. Perform that first reboot while you
have physical access to the phone, then unlock it and test both connection paths.

Manual startup and diagnostics:

```sh
bash ~/start.sh
pgrep -x sshd
pgrep -x cloudflared
tail -n 40 ~/server/logs/startup.log
tail -n 40 ~/server/logs/tunnel-startup.log
tail -n 40 ~/server/logs/cloudflared.log
```

A process ID or a startup request does not prove a healthy external connection.
Confirm the connector is Healthy in Cloudflare and test SSH from the laptop.
For Tailscale, connect to the phone's Tailscale IP on port 8022 with its Termux
username. For Cloudflare, keep using your existing `homessh` SSH configuration.

Atlas starts through its own `50-atlas-api` boot hook and supervised API service.
The host scripts do not start or stop the AI application. APK recovery buttons
remain follow-up work, and must understand which mechanism owns the tunnel before
attempting recovery.

Reference: https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/run-parameters/
