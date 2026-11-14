# Atlas energy orb — 0.12.0 / build 13

## Rendering

`mobile/Atlas.UI/wwwroot/atlas-orb.js` replaces the humanoid Three.js model with a dependency-free Canvas 2D renderer. It projects three-dimensional shell points and gently deforming orbital curves with perspective. Back orbital paths/nodes draw first; a near-black core occludes the back paths, the rim-weighted blue point shell draws next, and front paths/nodes draw last. The centre stays dark. Independently moving cyan-white nodes leave short fading tails. Sparse outer dust adds depth.

This is a live procedural visual, not a rotating reference image or flat spinner. No WebGL or extra permission is required. The old humanoid assets and unused Three.js bundle have been removed. Orb vectors replace portraits in the header, setup, message thumbnails, launcher and splash. The static fallback uses the same shell/orbital identity.

Full view uses 1,100 points on lower tiers or 1,800 on standard tiers; the compact chat orb uses 350/700. Pixel ratio is capped at 1.25/1.75 and frames at 24/30 fps. Sustained expensive draws lower density and resolution further. Motion uses elapsed time and exponential state interpolation, with bounded delta time after a pause.

`AtlasOrb.razor` initializes once per mounted view. The existing companion page remains mounted between visits and passes its visibility to the renderer. Intersection, document visibility, MAUI activation, and the workspace drawer also pause rendering. Resume does not fast-forward the orb. Disposal cancels the sole frame callback, disconnects observers and media listeners, releases canvas backing buffers, and removes interop references. Canvas initialization/drawing/context failures show one static SVG with concise optional details. No portraits or overlapping fallback background remain.

Reduced-motion preference freezes orbital motion and breathing, allows only gentle state interpolation, then stops scheduling frames once settled. No strobe or rapidly repeating error animation is used.

## Actual application events

| Visual state | Production trigger |
| --- | --- |
| Ready / idle | Connected, no pending AI request and no confirmed playback |
| Thinking | Chat request is running and a user message has pending delivery; unrelated UI loading does not trigger it |
| Speaking | Android installed TTS engine reports utterance start; ends on done, stop, error, navigation cancellation or backgrounding |
| Disconnected | No connection, or the repository is using its offline cache |
| Error / Needs attention | Existing readable AppState error; one restrained 1.5-second indication on entry, not a repeating flash |
| Listening | Not emitted: this app has no active recording or speech-recognition capability. The renderer accepts the state for a future real capture host; there is no pretend Listen button |

## Voice scope

Say hello, Read latest reply, Read aloud and Stop retain their explicit actions. Android uses the same installed system TTS capability and existing TTS-service manifest query. A native utterance-progress listener distinguishes a queued request from playback start. The engine is stopped/shut down and callbacks released after each request. Long text is chunked within Android's input limit while preserving surrogate pairs. Authentication, API, backend, chat recovery and cache formats are unaffected.

The installed voice engine does not provide playback amplitude to Atlas. Speaking therefore uses a quiet rhythmic animation only between actual playback callbacks, not claimed amplitude synchronization. Other MAUI hosts keep their existing TextToSpeech playback; if no start callback is available, the UI says playback was requested, keeps Stop available, and does not invent a speaking pulse. Muted system output cannot be detected; engine start confirms playback lifecycle, not that the user hears audio.

## Verification and limits

- 23 .NET tests passed, including new queued-vs-started playback and presence/error tests plus existing authentication/cache/chat recovery, Markdown, UI state, speech cancellation and background tests.
- Seven dependency-free Node renderer tests passed: time-based motion, state changes, one loop, navigation/offscreen/background pause and resume, reduced motion, tier limits/adaptive density, context failure and disposal.
- Shared UI / HTML fixture build completed without warnings. JS syntax and Python visual/Android script compilation passed.
- Actual renderer frames were rasterized with a software Canvas implementation and visually inspected. These are renderer frames, not phone screenshots or proof of Android performance.
- Browser CI covers orb states, static fallback, compact-chat placement, small widths, larger text and composer/navigation clearance. Android smoke checks the installed setup orb and background/resume without backend credentials.
- Local Chromium and native Android/Windows/device execution are unavailable in this workspace. Physical Samsung A12 frame rate, installed voice-engine callbacks, native keyboard, real server workflows and resumed graphics still need device acceptance. No listening or amplitude synchronization is claimed.
