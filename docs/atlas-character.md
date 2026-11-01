# Atlas identity and live character

Atlas uses the approved hooded blue-and-black companion with cyan eyes, silver hair, and an orbital halo. The avatar and full-body artwork were derived from the original character sheet using built-in image generation; bundled WebP derivatives keep mobile decoding small. Full-resolution source artwork remains a separate character asset.

`mobile/Atlas.UI/wwwroot/atlas-3d.js` constructs a stylized articulated 3D interpretation using Three.js 0.187.0. It includes head and arm pivots, blinks, idle motion, an orbiting halo, a wave, drag/keyboard rotation, and mouth opening while speech is active. This is original procedural geometry; it is not an exact sculpt of the detailed illustration or a VRM/GLB import. A future artist-produced model can replace the geometry while keeping the state/voice bridge.

Voice is native MAUI TextToSpeech through IAtlasSpeech. Nothing is recorded, no microphone permission is used, and no speech plays automatically. Read aloud and Say hello are explicit actions; Stop, navigation away from the companion/chat, disconnect, and app deactivation cancel speech. Availability and voice quality depend on the device's installed text-to-speech engine and voice data. Mouth motion follows the speech task's lifecycle; it is approximate animation, not phoneme-level lip-sync.

Rendering caps device pixel ratio at 1.5 and drawing at 30 fps, skips drawing when offscreen/backgrounded, respects reduced-motion preference for idle movement, and disposes geometry/materials/context on navigation. WebGL initialization failure shows the original mascot instead.

Verification includes speech lifecycle/cancellation tests, browser WebGL rendering/state/disposal checks, responsive screenshots, Android/Windows compilation, and the installed Android smoke workflow. No backend or Groq API credentials are required for these checks.
