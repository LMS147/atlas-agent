# Workspace backup and recovery

This Python standard-library utility backs up the local `DATA_DIR`: conversation SQLite databases, agent identity, memories, uploaded files and existing memory snapshots. SQLite files are copied through the SQLite backup API and checked for integrity. A manifest records SHA-256 checksums. Archives are private (0600 on Unix) but **not encrypted**; keep them in protected storage and encrypt off-device copies.

This is an offline backup: stop the API supervisor **and Telegram** before creating or restoring a backup so files and database records describe the same moment. `--services-stopped` is your explicit acknowledgement, not automatic process detection. Confirm both processes have stopped; Termux helpers may automatically restart supervised services, so use `deployment/termux/stop.sh` and `stop-telegram.sh` as applicable. Resume services after the operation.

Use the absolute `DATA_DIR` configured for your deployment, not a guessed `./data`. Store archives outside that directory.

```sh
python deployment/backup/atlas_backup.py create --data-dir /absolute/atlas-data --archive /absolute/private-backups/atlas-2026-11-01.zip --services-stopped
python deployment/backup/atlas_backup.py verify --archive /absolute/private-backups/atlas-2026-11-01.zip
python deployment/backup/atlas_backup.py restore --archive /absolute/private-backups/atlas-2026-11-01.zip --destination /absolute/atlas-restore-test --services-stopped
```

Restore requires a new destination and never replaces a live workspace. It validates entries and checksums before extracting, rejects traversal, symlinks and excessive archives, and checks restored SQLite databases. Test the restored directory with an isolated API instance and separate credentials before switching production `DATA_DIR`. Preserve the old directory as a rollback copy. Start the API with the recovered directory and verify history, memories, files and agent identity.

Keep at least seven daily and four weekly copies on a separate device or protected remote storage. Retention is an operator policy; this utility does not automatically delete archives or schedule downtime. Periodically perform the restore drill above. Credentials, `.env` and signing keys must live outside `DATA_DIR` and are not part of this backup. Keep a separate secure copy of server configuration. For `GH_REPO` memory mode, back up the external repository separately; this tool only captures local workspace files.

Run regression tests with `python -m unittest discover -s deployment/backup -p 'test_*.py'`.
