# Atlas visual assets

The current Atlas identity is an abstract blue energy orb, implemented procedurally rather than from generated humanoid artwork. The previous character artwork and Three.js model are no longer bundled. Their historical prompts remain available in Git history.

- `mobile/Atlas.UI/wwwroot/atlas-orb.js`: animated point shell, projected orbital curves, travelling light nodes and fading tails.
- `mobile/Atlas.UI/wwwroot/atlas/orb.svg`: lightweight static fallback and thumbnails.
- `mobile/Atlas.Mobile/Resources/AppIcon/appicon.svg`: simplified orb launcher icon.
- `mobile/Atlas.Mobile/Resources/Splash/splash.svg`: matching splash orb.

The orb has no face, body, eyes, clothing, robot features or microphone interaction. All assets are bundled and require no network requests. See [implementation and state mapping](atlas-character.md).
