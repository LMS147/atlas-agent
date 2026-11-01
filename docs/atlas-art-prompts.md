# Atlas artwork prompts

Mode: built-in image generation, identity-preserving edits of the approved **Atlas: Blue-Lit AI Companion** reference sheet. Transparent background requested for both assets. This is separate from the procedural 3D geometry and native speech system.

Project assets:

- `mobile/Atlas.UI/wwwroot/atlas/avatar.webp` — optimized avatar portrait.
- `mobile/Atlas.UI/wwwroot/atlas/mascot.webp` — optimized full-body mascot.
- `mobile/Atlas.UI/wwwroot/atlas-3d.js` — the articulated live 3D interpretation.

The full-resolution generated PNGs were retained separately. The WebP derivatives preserve the artwork and transparency while keeping app decoding and downloads small.

## Full-body mascot prompt

Use case: identity-preserve / background-extraction. Asset type: production app mascot PNG with actual transparent alpha. The input image is the approved Atlas character reference sheet. Create ONE isolated full-body Atlas character, preserving this exact identity: sleek smooth black synthetic face, friendly glowing cyan eyes, short silver-gray hair, navy-black hooded layered coat, scarf, black utility trousers and sneakers, small blue A chest emblem, thin luminous blue orbital halo with one small orbiting dot. Same polished stylized 3D rendering as reference, approachable young adult AI companion, calm friendly expression. Full body centered in a portrait composition, natural standing pose, one palm slightly open holding the small cyan orbital light as in left figure. Keep all hood, halo, hands and shoes inside image with 8 percent breathing room. True transparent background, clean cutout silhouette, natural blue edge light without large detached glow. No background scene, no floor, no shadows outside character, no typography, no name captions, no reference sheet, no extra characters. Preserve the outfit and face rather than redesigning Atlas. Intended to display at 180-260 CSS pixels in a dark slate mobile app.

## Avatar prompt

Use case: identity-preserve. Asset type: square app avatar portrait, transparent alpha background. From the approved Atlas reference sheet, produce ONE centered head-and-shoulders portrait of exactly the same Atlas character shown in the central portrait: smooth black synthetic face, friendly cyan glowing eyes and cyan eyebrows, silver-gray swept hair, navy hood up, black scarf, blue-accented round ear pieces, slim blue orbital ring with a single small cyan orbiting dot. Preserve the face shape, expression, outfit, proportions, silver hair and polished stylized 3D materials from the reference. Face looking gently toward viewer, sympathetic calm confident expression, no exaggerated grin. A clean recognizable face at 32-48 pixels. Frame closely but include the full hood and halo, head occupying about 65 percent of square, shoulders cropped at lower edge. Genuine transparent background outside silhouette, no black rectangle, no decorative background, no text, no labels, no border, no extra portraits. Controlled cyan rim light, no enormous surrounding glow. This is the same character as the approved reference, not a redesign.
