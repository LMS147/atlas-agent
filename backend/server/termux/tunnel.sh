#!/data/data/com.termux/files/usr/bin/bash
# One retrying connector for the existing remotely-managed Cloudflare tunnel.
set -euo pipefail
umask 077

mkdir -p "$HOME/server/logs" "$HOME/server/.run"
command -v flock >/dev/null || { echo 'Install util-linux for flock.' >&2; exit 1; }
command -v cloudflared >/dev/null || { echo 'Install cloudflared first.' >&2; exit 1; }

exec 9>"$HOME/server/.run/cloudflared.lock"
flock -n 9 || { echo 'The tunnel launcher is already running.'; exit 0; }

# Do not duplicate a connector launched by a supervisor or an older boot script.
if pgrep -x cloudflared >/dev/null; then
    echo 'A cloudflared process already exists. Keep one startup owner.' >&2
    exit 1
fi

child=''
stop() {
    trap - TERM INT
    if [[ -n "$child" ]]; then
        kill "$child" 2>/dev/null || true
        wait "$child" 2>/dev/null || true
    fi
    exit 0
}
trap stop TERM INT

while true; do
    if [[ ! -s "$HOME/token.txt" ]]; then
        echo 'Create the private, nonempty ~/token.txt before starting the tunnel.' >&2
        exit 1
    fi
    # Requires cloudflared >= 2025.4.0. The token itself stays out of arguments.
    cloudflared tunnel --no-autoupdate run --token-file "$HOME/token.txt" \
        >> "$HOME/server/logs/cloudflared.log" 2>&1 &
    child=$!
    result=0
    wait "$child" || result=$?
    child=''
    printf 'Cloudflare exited (%s). Retrying in 10 seconds.\n' "$result" >&2
    sleep 10 &
    child=$!
    wait "$child" || true
    child=''
done
