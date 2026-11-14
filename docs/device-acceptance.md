# Real-device acceptance checklist

Status: **not yet executed on the owner's phone/server**. CI checks are complementary, not proof that these scenarios pass on a physical device. Use a disposable workspace, fake files and a test token first. Never attach credentials, personal conversations or server addresses to public test logs.

Record app version, public signing certificate fingerprint, Android version, phone model, WebView version, backend revision and pass/fail evidence for each case.

| Scenario | Acceptance criteria |
|---|---|
| Installation and update | Atlas name and blue orb appear on the launcher; a newer APK signed with the same permanent key updates without losing connection settings or cached chats. |
| Setup and credentials | HTTPS connection succeeds; incorrect token fails clearly; Remember restores the connection; Disconnect removes stored credentials. |
| Real chat | Send once, receive one reply, close/reopen, and restore both messages from the backend. |
| Connection interruption | Interrupt network during a request; restore it and check for the existing reply before retrying. No duplicate inference or tool effects. |
| Files | Upload/download a disposable binary, compare bytes, edit UTF-8 text, test conflicting edits, and verify unsaved-change prompts. Save downloaded files through the native share destination. |
| Memory | Create/edit/delete a test fact; preview compaction; ensure conflicting revision changes are rejected. |
| Navigation and keyboard | All bottom tabs and drawer entries work, Back closes the drawer first, text input remains visible above the keyboard, and unsaved edits are protected. |
| Lifecycle | Background during speech and chat; speech stops, app resumes, pending delivery can be checked, and the particle orb pauses offscreen. |
| Accessibility | Enable TalkBack and largest text/display size; controls have useful labels, visible focus, readable content and no inaccessible offscreen actions. Test a narrow screen and landscape. |
| Migration | Recover Kotlin-only history before replacing an older installation. Server-backed history restores in MAUI; device-only data is not automatically imported. |
| Recovery | Stop services, create/verify a backup, restore to a new test directory and validate conversations, memory and uploaded bytes before changing production DATA_DIR. |

Do not mark a row passed from a build log alone. Keep unresolved failures and reproduction steps in an issue. Re-run affected scenarios after fixes.
