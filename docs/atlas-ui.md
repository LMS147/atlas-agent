# Atlas mobile UI — 0.11.0 foundation / 0.12.0 orb

Atlas remains the personal AI application. Server administration lives in the separate Server-management project. This change affects presentation only; API routes, token storage, cache isolation, request recovery, backend operations, and data models are unchanged.

## Shared design

The shared stylesheet now owns the navy / mint palette, eight-point spacing scale, typography, touch targets, focus rings, borders, and responsive layout. The five bottom destinations remain Chat, Memory, Atlas, Files, and More. The header is compact; More groups workspace pages, maintenance, agent information, and connection settings.

Navigation height is measured rather than assumed by the content and composer. Safe-area space is included, and visual viewport changes are considered for hosts whose keyboard overlays the layout. Android retains its existing AdjustResize setting. The delegated composer listener grows the field to 160 px before scrolling internally and is disposed with the layout.

## Screens

- Connect: compact original artwork, early connection form, HTTPS/token validation consistent with AtlasApi, token visibility, secure persistence, and expandable setup help.
- Chat: compact empty state and starters, original message rendering/actions, bounded composer, small cached-history notice with a real new-chat action. Cached messages are retained.
- Memory: primary Remember action, grouped search/category controls, secondary refresh and cleanup preview, readable rows, distinct empty/search-empty/loading/error presentation. Existing preview, revision, and apply behavior is retained.
- Atlas: a procedural blue particle orb, shared with the empty Chat screen. One Canvas renderer or matching static SVG is visible at a time. The companion stays mounted and pauses offscreen. See [orb implementation](atlas-character.md) for the current identity and verification.
- Files: compact folder/document rows, editable/read-only labels, working breadcrumbs, contextual transfer limits, accessible per-file actions, and indeterminate upload feedback. The API provides no byte-progress events, so no percentage is fabricated. Downloads, read-only behavior, text editing, and discard confirmation are retained.
- Maintenance: compact tool list and existing preview-before-apply cleanup workflow.
- Agent profile: semantic headings, paragraphs, lists, emphasis, code, blockquotes and safe HTTP(S) links. The small, dependency-free Markdown reader encodes source HTML, blocks executable URLs, and does not fetch remote images. Source content and the read-only contract are retained.

## Files

- `mobile/Atlas.UI/wwwroot/atlas.css`: shared visual system and responsive layouts.
- `mobile/Atlas.UI/Components/AtlasRoot.razor`, `AtlasIcon.razor`: navigation and outline icons.
- `mobile/Atlas.UI/Components/AtlasOrb.razor`, `wwwroot/atlas-orb.js`: renderer and fallback lifecycle.
- `mobile/Atlas.UI/wwwroot/atlas-navigation.js`: composer/viewport sizing and existing drawer focus behavior.
- `mobile/Atlas.UI/Pages/`: existing screens and their unchanged operation handlers.
- `mobile/Atlas.UI/Components/ProfileMarkdown.cs`: encoded Markdown presentation.
- `mobile/Atlas.Core.Tests/ProfileMarkdownTests.cs`: semantic output and injection regression checks.
- `mobile/tests/Atlas.VisualChecks/Program.cs`, `mobile/tests/visual_check.py`: page fixtures and expanded browser assertions.
- `mobile/Atlas.Mobile/Atlas.Mobile.csproj`, `MainPage.xaml`: version 0.12.0/build 13 and matching native background.

## Verification

Local checks: 20 .NET tests passed, including existing repository, cache, streaming/recovery, speech, UI state and message encoding tests, plus the profile Markdown tests. The shared UI and visual fixture project built without warnings. HTML snapshots rendered for setup, setup loading/error, empty chat, conversation, cached chat, empty/populated memory, companion, files, maintenance, profile, settings and More. JavaScript syntax and Python check-script compilation passed.

Local Chromium cannot launch under the workspace's process restrictions. No local screenshots, pixel/overflow results, live 3D rendering results, or native APK/device keyboard results are claimed. The existing MAUI CI visual job now captures the expanded screen set at 320, 360, 390, 768 and 1440 px, checks navigation/overflow, static orb fallback, profile semantics, large filenames/text and a reduced-height composer. Its output is uploaded as `atlas-hybrid-visual-results`. Static fixtures use test data only and do not prove live endpoint or native keyboard behavior.

On a device, still verify keyboard open/close, orientation and safe-area changes, text scaling, animated orb versus fallback, authentication, real chat send/recovery, memory editing/preview, upload/download/edit and read-only files before releasing the signed APK.
