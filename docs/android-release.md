# Permanent Android signing

The manual **Atlas signed release APK** workflow publishes a Release APK using a permanent key. It fails if any signing secret is missing; it never generates or substitutes a debug key. Regular MAUI CI continues to produce clearly named development APKs for emulator checks. The release workflow has not yet been exercised with the owner's signing secrets.

## One-time setup

Create or recover your permanent signing key on your own computer. Prefer the existing signing key if you have already distributed a permanently signed version. For a new key, run this interactively (passwords are prompted, not placed in shell history):

```sh
keytool -genkeypair -v -keystore atlas-release.keystore -alias atlas -keyalg RSA -keysize 4096 -validity 10000
```

Back up the keystore, alias and passwords in secure locations outside this repository. Do not generate a new key for every release. Losing the key prevents compatible updates to installations signed with that key.

In GitHub Settings → Environments, create `android-release`. Add these environment secrets:

| Secret | Value |
|---|---|
| `ATLAS_ANDROID_KEYSTORE_BASE64` | Base64 encoding of the complete keystore file |
| `ATLAS_ANDROID_KEY_ALIAS` | Signing alias, for example `atlas` |
| `ATLAS_ANDROID_KEY_PASSWORD` | Key password |
| `ATLAS_ANDROID_STORE_PASSWORD` | Keystore password |

PowerShell can encode the file: `[Convert]::ToBase64String([IO.File]::ReadAllBytes('atlas-release.keystore'))`. Paste it directly into the GitHub secret; never commit it or send it in chat.

Run **Actions → Atlas signed release APK → Run workflow** on the intended source revision. Download `atlas-release-android-apk`. The workflow verifies the APK signature and prints the public certificate fingerprint; record that fingerprint and compare future releases. Increase `ApplicationVersion` for every distributed update.

## Existing development installations

The application ID stays `com.atlas.ai.hybrid`. Android requires the same signing certificate for an in-place update. A new permanent key cannot update an APK signed with a different temporary CI debug key. Do not uninstall an existing app until you have recovered server history and exported any device-only data you need. Confirm the migration using a spare device before replacing your primary installation.

The release workflow uses environment-backed signing passwords, as documented in [Microsoft's Android publishing guide](https://learn.microsoft.com/dotnet/maui/android/deployment/publish-cli?view=net-maui-10.0).
