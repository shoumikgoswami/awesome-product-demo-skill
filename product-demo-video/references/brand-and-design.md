# Brand detection and design

## What gets detected (`scripts/extract_brand.py`)
Input: the screenshots (+ logo, weighted 6x). It buckets pixels by hue and keeps only *vivid* ones (saturation > 0.38) for the accent, and
*dark saturated* ones for the base (the colour of a navy sidebar or dark header). Output `theme.json`:

| Key | Meaning |
|---|---|
| `mode` | `dark` (default; light screenshots pop on a dark stage) or `light`. `--mode` forces it |
| `colors.accent` | the brand's most common vivid colour; nudged until it has >= 3.2:1 contrast against the background |
| `colors.accent2` | second distinct vivid colour, else a derived neighbour (a note says which) |
| `colors.bgDeep / bg / bgLight` | background gradient built from the base hue (dark brand colour if found, else the accent hue) |
| `colors.text / textMuted / onAccent / card` | readable text colours for the chosen mode; `onAccent` picked by contrast |
| `font` | one of the bundled families (default `inter`) |
| `_meta` | confidence, candidate colours, notes |

Open `brand-swatches.png` and compare with the product. **It is a heuristic**: greyscale UIs have no vivid colour (confidence `low`, accent
defaults to blue), UIs with many chart colours can pick a chart colour over the brand colour, photos skew results.
Override: `--primary "#EE8F26"`, `--accent2`, `--base "#262F46"`, `--mode`, or edit `theme.json` directly. The manifest's `theme` key overrides `theme.json` per video.
If the user gives a product URL, fetch it and read `theme-color`, the logo and the primary button colour from the page/CSS to pick `--primary`.

## Choosing mode and font
- **dark** (default): works for almost everything; gives the enterprise look. **light** for brands that are white/pastel, or when the screenshots are themselves dark (then a light stage separates them).
- Fonts bundled (offline, via fontsource): `inter` (neutral, default), `poppins` (friendly, geometric), `manrope` (modern SaaS), `dm-sans` (clean, humanist),
  `plus-jakarta-sans` (premium/fintech), `space-grotesk` (technical/dev-tool). Pick from the product's personality; avoid asking the user.
- Brand names keep their casing everywhere (the template never uppercases text except the small eyebrow labels).

## Logo
Best: PNG with transparency or SVG, at least ~300 px wide. The header uses it at 54-62 px height. If its pixels would vanish against the background (dark text on dark stage)
`build_timeline.py` automatically seats it on a white (or dark) rounded plate. No logo -> the product name is set as a wordmark. Tell the user a vector logo looks crisper.

## What the video looks like (so you can describe and tune it)
- 1920x1080. Stage = background gradient + soft accent glow top-right.
- **Header**: logo, divider, chapter eyebrow ("Step 2 of 4") + chapter title; step tracker pills top-right (done = check, active = accent fill with title, upcoming = outline).
- **Window card**: rounded, shadowed; sized to the most common screenshot aspect ratio so it never jumps; other aspect ratios are letterboxed over a blurred copy.
- **Motion**: zoom/pan (0.7 s ease), accent highlight box with a pulsing glow, cursor with curved glide + click ripple, 0.3 s crossfade (same page) or 0.35 s push (new page).
- **Captions** under the card: 42 px, current word in accent. **Progress line** along the bottom edge in accent.
- **Intro** (~5 s): logo, eyebrow, staggered headline with highlighted phrase, subhead, floating hero screenshot, up to 3 point cards. **Outro** (~5 s): headline, subhead, URL/path pills, up to 3 cards, closing line.

## Intro / outro copy
Take it from what the user supplied: product page text, the script, UI labels. Pattern that works: headline = the outcome in <= 9 words with the key phrase highlighted;
subhead = one sentence of who/how long; points = the 3 steps; outro headline = a call to action; pills = the real URL or menu path; closing = the next step.
No invented numbers, customers or promises.

## Customising the template (only for new design features)
`renderer/src/` is plain React: `Stage.tsx` (layout, fades, progress), `Header.tsx`, `SceneView.tsx` (zoom, highlight, cursor, chips, blur, callouts, typing),
`Captions.tsx`, `Intro.tsx`, `Outro.tsx`, `Logo.tsx`, `utils.ts` (card size constants `CARD_MAX_W/H`, easing), `types.ts` (the timeline schema).
Run `npx remotion studio --props=public/<video>/props.json` in `renderer/` to scrub the video live. Animate only with
`useCurrentFrame()` + `interpolate()` - never CSS transitions/animations (they do not render). Adding a field = extend `types.ts`, read it in `build_timeline.py`, draw it in a component.
`setup_renderer.py` refreshes `src/` from the skill each run, so keep custom edits in a fork of the template or re-apply them.
Not supported yet: vertical/square canvases, multiple languages in one video, real screen recordings beyond short `clip` scenes.
