"""Linux/Termux metrics without native dependencies; unavailable is never zero."""
import os
from pathlib import Path
import resource
import shutil
import threading
import time

_lock = threading.Lock()


def _cpu():
    values = [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + (values[4] if len(values) > 4 else 0)


def snapshot(app):
    unavailable = []
    def read(label, callback):
        try:
            return callback()
        except (OSError, ValueError, IndexError, KeyError, StopIteration):
            unavailable.append(label)
            return None
    # Serialize short samples so concurrent refreshes do not create misleading baselines.
    with _lock:
        first = read('device CPU', _cpu)
        usage = resource.getrusage(resource.RUSAGE_SELF)
        process_first = usage.ru_utime + usage.ru_stime
        started = time.monotonic()
        time.sleep(0.2)
        second = read('device CPU', _cpu) if first else None
        usage = resource.getrusage(resource.RUSAGE_SELF)
        process_cpu = max(0, 100 * (usage.ru_utime + usage.ru_stime - process_first) / (time.monotonic() - started))
    cpu = None
    if first and second and second[0] > first[0]:
        cpu = min(100, max(0, 100 * (1 - (second[1] - first[1]) / (second[0] - first[0]))))
    def ram():
        values = {line.split(':')[0]: int(line.split()[1]) * 1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ('MemTotal', 'MemAvailable')}
        return dict(total_bytes=values['MemTotal'], available_bytes=values['MemAvailable'], used_bytes=values['MemTotal'] - values['MemAvailable'])
    def rss():
        return int(next(line for line in Path('/proc/self/status').read_text().splitlines() if line.startswith('VmRSS:')).split()[1]) * 1024
    def disk():
        info = shutil.disk_usage(app.state.settings.data_dir)
        return dict(total_bytes=info.total, used_bytes=info.used, free_bytes=info.free)
    with app.state.metrics_lock:
        counts = dict(app.state.metrics)
    return dict(sampled_at=int(time.time() * 1000), device_cpu_percent=cpu, process_cpu_percent=round(process_cpu, 2),
                ram=read('device RAM', ram), process_rss_bytes=read('process RAM', rss), storage=read('storage', disk),
                device_uptime_seconds=read('device uptime', lambda: int(float(Path('/proc/uptime').read_text().split()[0]))),
                service=dict(pid=os.getpid(), uptime_seconds=int(time.monotonic() - app.state.started), threads=threading.active_count(), **counts),
                unavailable=sorted(set(unavailable)))
