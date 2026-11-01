# Atlas MAUI Blazor Hybrid

Atlas Hybrid 0.6.2 is the new C# client. Open **mobile/Atlas.sln** in Visual Studio with .NET 10 and the .NET MAUI workload. Android is the first installable target; the Windows host is also compiled in CI. iOS/Mac Catalyst targets have not been added or tested.

| Project | Responsibility |
| --- | --- |
| Atlas.Mobile | Native MAUI host, secure credentials, file picker/share sheet, window lifecycle |
| Atlas.UI | Reusable Razor screens and dark blue responsive CSS |
| Atlas.Core | Typed FastAPI client, SQLite cache, workspace isolation and request recovery |
| Atlas.Core.Tests | Mock HTTP + actual SQLite integration tests; no Groq credentials |

## Build

Use .NET 10 SDK, the MAUI workload and the appropriate Android SDK/JDK (the .NET 10 Android toolchain uses JDK 21). The MAUI NuGet packages track the installed workload's `MauiVersion`.

```powershell
dotnet workload install maui
dotnet build mobile/Atlas.Mobile/Atlas.Mobile.csproj -t:InstallAndroidDependencies -f net10.0-android -p:AndroidSdkDirectory="C:\Android\Sdk" -p:AcceptAndroidSDKLicenses=True
dotnet build mobile/Atlas.Mobile/Atlas.Mobile.csproj -f net10.0-android -c Debug -p:AndroidPackageFormats=apk -p:EmbedAssembliesIntoApk=true
```

Set `ANDROID_HOME` to your actual Android SDK location when building from a terminal. On Windows, run the Windows target with Visual Studio or `dotnet build mobile/Atlas.Mobile/Atlas.Mobile.csproj -f net10.0-windows10.0.19041.0`. Windows requires WebView2. On Linux, the framework-independent core/UI checks do not need a MAUI workload:

```sh
dotnet test mobile/Atlas.Core.Tests/Atlas.Core.Tests.csproj
dotnet build mobile/Atlas.UI/Atlas.UI.csproj
```

GitHub Actions **MAUI Hybrid CI** uploads `atlas-hybrid-android-apk`. Extract and install the `*-Signed.apk` file. This is a development APK; configure a durable signing key for distributed production updates. Default CI debug signing keys are not a guaranteed stable upgrade identity.

## Connect

The setup screen pre-fills `https://atlas-api-a9s1.onrender.com/`, but the URL is editable. For your own phone server, use its HTTPS tunnel address and that server's `ATLAS_API_TOKEN`. Enter the token in the app, never in source code. Optional connection persistence uses native MAUI `SecureStorage`. Groq stays in FastAPI's environment; no provider key is in the APK. No automatic inference retries or HTTP redirects are enabled.

## Migration and feature status

The new Android package is **com.atlas.ai.hybrid**, displayed as **Atlas Hybrid**. It installs alongside **com.atlas.ai** (Kotlin). Both clients remain in this repository during migration. Do not uninstall the old app to install this one.

Implemented: authenticated HTTPS setup; secure optional token restore; named conversations; rename/delete confirmations; selected conversation; paged server history; per-workspace SQLite cache; cached offline opening; durable message state; read-only reply checks; confirmed same-ID delivery retries and fresh requests; memory list/search/filter/create/edit/delete/compaction previews; workspace file upload/download/text editing with revisions; read-only canonical documents/profile; actual monitoring with nullable restricted metrics and foreground-only polling.

Downloaded files are stored in a uniquely named private cache folder, then opened in the native share sheet. Pick a destination such as Files/Drive or an appropriate app. These temporary cache copies may be cleared by the OS; save important downloads to a chosen destination. Text edits stay open on failed/conflicting saves; unsaved-close prompts before discarding. Confirmed memory/conversation operations act on the SAME backend workspace as the Kotlin app.

Kotlin Room and its Keystore records are not imported automatically. Re-enter the Atlas token and restore server conversations. Device-only history, unresolved Kotlin requests, and data already lost from free Render storage cannot be reconstructed from the server. Keep Kotlin available to recover/check its unresolved messages before moving ongoing work. If the server no longer contains a cached conversation, Hybrid preserves its own cache as unavailable instead of silently recreating the server chat; deletion tombstones purge that cache.

The Python backend, Telegram integration, Termux scripts, SQLite server data and API contracts remain unchanged. Task automation, character animation, embedded Groq keys, and a browser-hosted web frontend are not part of this client migration. Razor components can be reused in a future web host with appropriate native-service adapters.

## UI state updates

`AtlasRoot` publishes the mutable `AppState` through a non-fixed `CascadingValue`; pages inherit `AtlasPage` and receive it as a cascading parameter. Injecting the singleton alone does not notify parameterless child components when a parent rerenders. This previously left setup controls disabled after startup completed.

## Verification limits

CI compiles Razor, executes HTTP/SQLite tests, builds the Android APK, compiles Windows, and runs an Android emulator touch smoke test. The smoke test types into the setup fields, checks that Connect enables before token blur, taps Connect against a deliberately unreachable local HTTPS endpoint, verifies error recovery, and toggles Remember. It uses only a fake token and makes no inference call. Debug builds enable WebView inspection for this test; release builds do not. Real device file destinations, secure-storage behaviour, keyboard/back handling, accessibility, screen layouts and lifecycle timing need device testing. Backend/Groq integration requires your configured server. Never treat a successful build as a real paid/provider inference check.
