#!/data/data/com.termux/files/usr/bin/bash
# Host startup only. Atlas has its own supervised API service.
set -euo pipefail
umask 077

mkdir -p "$HOME/server/logs" "$HOME/server/.run"
command -v flock >/dev/null || { echo 'Install util-linux for flock.' >&2; exit 1; }
exec 8>"$HOME/server/.run/start.lock"
flock -n 8 || { echo 'Server startup is already in progress.'; exit 0; }

termux-wake-lock
pgrep -x sshd >/dev/null || sshd

if pgrep -x cloudflared >/dev/null; then
    echo 'SSH is available and an existing Cloudflare connector is running.'
    exit 0
fi
if [[ ! -f "$HOME/tunnel.sh" || ! -s "$HOME/token.txt" ]]; then
    echo 'SSH is available. Install ~/tunnel.sh and the private ~/token.txt first.' >&2
    exit 1
fi

nohup bash "$HOME/tunnel.sh" >> "$HOME/server/logs/tunnel-startup.log" \
    2>&1 < /dev/null 8>&- &
echo 'Tunnel startup requested. Check ~/server/logs/tunnel-startup.log and Cloudflare status.'
