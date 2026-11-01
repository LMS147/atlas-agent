# MAUI migration status

**Use `mobile/` for new Atlas app development.** It contains the .NET MAUI Blazor Hybrid client. `android/` is the legacy Kotlin client, retained for existing users and data recovery. The native package IDs differ: `com.atlas.ai.hybrid` versus `com.atlas.ai`.

Connect MAUI to the same server with the same token to restore conversations stored on that server. MAUI has its own SQLite cache and SecureStorage credentials; it cannot directly read the Kotlin app's private Room database or Keystore.

## Before replacing an older installation

1. Keep the Kotlin app installed and check unresolved requests on the original server before retrying them.
2. Verify server-backed conversations are visible in MAUI. Load earlier history where required.
3. Make a verified server workspace backup using `deployment/backup/atlas_backup.py`.
4. Preserve device-only messages using the existing app or developer-assisted database extraction on a testable device. A supported Kotlin export/MAUI import flow is **still pending**. Do not uninstall the legacy app assuming the server holds its entire local history.
5. Test permanently signed APK updates on a spare device. A new signing key cannot replace a differently signed development installation in place.

A future import must preview counts, validate schema and limits, isolate server/credential scopes, preserve source IDs, and import historical records without submitting AI requests. Pending/failed legacy deliveries must never be silently replayed. This document does not claim that importer exists.
