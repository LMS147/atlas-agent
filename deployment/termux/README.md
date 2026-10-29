# Atlas API service on Termux

Atlas can run under **termux-services/runit**, which restarts the API after a process crash. The installer registers only Atlas and can add a separate Termux:Boot hook. Existing SSH, Cloudflare, and other boot scripts remain in place.

## Configure once

Use the Termux and Termux:Boot apps from the same installation source. Open Termux:Boot once. In Samsung settings, allow Termux/Termux:Boot notifications, select unrestricted battery use, add them to Never sleeping apps, and avoid Power Saving while hosting the server. These are phone settings; repository scripts do not change them.

In Termux:

```sh
pkg install termux-services -y
```

Restart the Termux shell after installing the package. From your Atlas checkout, activate your Python environment, install backend/requirements.txt, and configure backend/.env. Keep the existing DATA_DIR so histories survive upgrades. A valid GROQ_API_KEY and a separate ATLAS_API_TOKEN (32+ characters) are required. The default API bind stays 127.0.0.1:8000 behind your HTTPS tunnel.

Stop any older manually started API first:

```sh
bash deployment/termux/stop.sh
```

Wait for shutdown to complete before switching to supervision. Keep the API checkout at a stable location; installed run scripts refer to its absolute path. If using a virtual environment, activate it or set ATLAS_PYTHON to its Python path before the installation command.

```sh
bash deployment/termux/install-service.sh --enable --boot
```

This validates configuration, registers the `atlas-api` service, enables it, waits for authenticated readiness, and creates only `~/.termux/boot/50-atlas-api`. Omitting `--enable` installs it disabled. Omitting `--boot` leaves your boot directory untouched. Credentials stay in backend/.env/environment; service/boot files contain paths, not API keys or tokens.

## Operate the service

| Command | Effect |
|---|---|
| `bash deployment/termux/service.sh status` | Supervisor status plus authenticated HTTP/PID health |
| `bash deployment/termux/service.sh health` | Confirm the responding API is the supervised process |
| `bash deployment/termux/service.sh restart` | Gracefully restart Atlas |
| `bash deployment/termux/service.sh stop` | Stop now; keep the enabled/disabled boot policy |
| `bash deployment/termux/service.sh start` | Start now |
| `bash deployment/termux/service.sh disable` | Stop and keep it disabled across supervisor/phone restarts |
| `bash deployment/termux/service.sh enable` | Enable automatic starts and start now |
| `bash deployment/termux/service.sh logs` | Show the most recent 100 log lines |

The original start.sh, stop.sh, and healthcheck.sh delegate to the registered service. Without a registration they retain the existing manual development behavior. Telegram remains separate with the *-telegram.sh helpers.

The API process also locks DATA_DIR. Another API process using the same directory is refused before initialization, protecting active requests from being marked interrupted by an accidental second start. Run the provided single-worker launcher. A duplicate server using another port cannot share that same DATA_DIR either.

## Restart and logs

runit supervises the foreground Python API process. Abnormal exits have a five-second restart delay; successful starts also acquire the Termux wake lock when the command is available. Shutdown/restart commands wait up to 30 seconds and report if a longer in-flight request is still shutting down; they do not forcibly kill it. Check status again before retrying administration commands.

Logs are in `$PREFIX/var/log/sv/atlas-api/current`, rotated around 1 MiB with five older files retained. Service files are under `$PREFIX/var/service/atlas-api`. Their marker prevents overwriting an unrelated service/checkout; existing enable/disable state is preserved when re-registering the same checkout. The boot hook starts Termux's service-daemon, respecting the service's persistent down flag. It acquires the wake lock only when Atlas is enabled.

A wake lock belongs to Termux as a whole. Atlas does not automatically release it on stop because your SSH or tunnel may still need it. Release it manually with termux-wake-unlock after all your phone services are stopped.

An Android force-stop or process policy can terminate Termux itself, including its supervisor. Reopen Termux/start services after a force-stop. Termux:Boot handles device boot; it does not override Android battery restrictions. Verify a real reboot on your A12 after configuring the apps. Automated CI covers Linux/runit process behavior, not Samsung battery/boot behavior.

## Chat recovery after a restart

Completed conversations/replies remain in SQLite. A request interrupted by a crash is marked `interrupted` on the next API start. In Android, **Check for reply** uses a read-only status endpoint. It never calls the agent. Finished replies can be restored, pending replies remain waiting, and interrupted/failed requests require confirmation before a fresh request.

If the server has no request record, Android offers **Retry delivery…**, reusing the original UUID only after confirmation. New clients require an existing conversation so a lost/replaced DATA_DIR cannot silently recreate an old chat. Provider rate limits return Retry-After guidance. Groq credentials, external tunnel connectivity, and an actual phone still need end-to-end checks in your configured environment.

The installer does not create DNS/tunnels, install apps, alter SSH, or copy the tunnel token from your existing setup. Keep using your current Cloudflare/SSH boot script alongside the Atlas hook.

References: [termux-services](https://github.com/termux/termux-services), [Termux:Boot](https://github.com/termux/termux-boot).
