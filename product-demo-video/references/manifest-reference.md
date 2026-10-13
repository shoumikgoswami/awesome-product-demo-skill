# manifest.json reference

`manifest.json` is the single source of truth for a video. `build_timeline.py` turns it (plus `theme.json` and the voice wavs) into the
timeline the Remotion template renders. Unknown keys are ignored, so keys starting with `_` can hold notes.
**Coordinates are fractions (0-1) of the screenshot**, so they survive any resolution: `x,y` = top-left of the box, `w,h` = its size.
Read them off `inspect/grid/<name>.png` (10% grid with labels).

## Top level
```json
{
  "title": "Acme - Getting started",
  "product": "Acme",
  "voice": "Sofia",
  "fps": 30,
  "stageLabel": "Product tour",
  "logo": "logo.png",
  "theme": { "mode": "dark", "font": "inter", "logoPlate": null, "colors": { "accent": "#14b8a6" } },
  "pacing": { "lead": 0.35, "gap": 0.25, "tail": 0.5, "firstLead": 0.6, "lastTail": 1.0, "hold": 3.0 },
  "vocabulary": "Acme, Kubernetes, SSO",
  "pronunciations": { "Acme": "Ack me" },
  "music": { "file": "music.mp3", "volume": 0.12 },
  "intro": { ... }, "outro": { ... }, "chapters": [ ... ], "scenes": [ ... ]
}
```
| Key | Default | Notes |
|---|---|---|
| `product` | from theme/title | shown as the wordmark when there is no logo, and in the header eyebrow |
| `voice` | `Sofia` | Magpie voices: Sofia, Aria, Jason, John, Leo |
| `fps` | 30 | 1920x1080 canvas (16:9) |
| `stageLabel` | `Product tour` | eyebrow text for chapters without a step number ("<Product> - <stageLabel>") |
| `logo` | none | file in the video folder (PNG with transparency / SVG best). If it would not read on the background it is put on a rounded plate automatically; `theme.logoPlate: null` disables, or give a colour |
| `theme` | from `theme.json` | overrides: `mode` dark/light, `font` (inter, poppins, manrope, dm-sans, plus-jakarta-sans, space-grotesk), `colors{...}` (keys below) |
| `pacing` | see above | seconds. Scene length = lead + sentence clips (+ gap between sentences) + tail |
| `vocabulary` | "" | prompt for faster-whisper caption alignment: product terms, names |
| `pronunciations` | {} | written form -> spoken form, applied to the text sent to the voice when a sentence has no `say` (captions always keep the written form). A `pronunciations.json` next to the manifest is merged in automatically |
| `music` | none | file or `{file, volume}`; fades in/out, loops, sits under narration |

Theme colour keys: `bgDeep, bg, bgLight` (background gradient + chip fill), `accent` (highlights, active step, current caption word),
`accent2`, `text`, `textMuted`, `onAccent` (text on accent fills), `card` (window card / blank-image backing).

## intro / outro (both optional; omit the key to skip)
```json
"intro": { "eyebrow": "Product tour", "headline": "From raw data to shared insight in minutes", "highlight": "shared insight",
           "subhead": "One supporting sentence.", "hero": "01-dashboard.png", "points": ["Pick a source", "Generate", "Share"], "seconds": 5 },
"outro": { "headline": "Ready to try Acme?", "highlight": "Acme", "subhead": "Build your first report in minutes.",
           "pills": ["acme.com/start"], "cards": [{"title": "Connect data", "body": "One line."}], "closing": "Start free at acme.com", "seconds": 5 }
```
`highlight` = words of the headline shown in the accent colour. `hero` defaults to the first screenshot; `points` max 3, `cards` max 3,
`pills` max 4 (monospace; use for URLs, menu paths, commands). Copy comes from the script/product page only. Intro/outro are silent
(music only); narration lives in the scenes.

## chapters
`[{"id": "c1", "step": null, "title": "Overview"}, {"id": "c2", "step": 1, "title": "Create a report"}]`
`step` numbers appear in the header ("Step 1 of 3") and the tracker pills top-right; `null` = not numbered (Overview, What's next).
Aim for Overview + 3-5 steps. Without `chapters` the whole video is one un-numbered chapter named after the title.

## scenes
```json
{ "id": "s03", "image": "03-new-report.png", "chapter": "c2", "transition": "auto", "chip": "Reports > New report",
  "sentences": [ {"id": "s03a", "caption": "Pick a data source.", "say": "Pick a data source."} ],
  "focus": [ ... ], "blur": [ ... ], "callouts": [ ... ], "type": [ ... ], "chips": [ ... ] }
```
| Key | Notes |
|---|---|
| `id` | unique; sentence ids must match `^[A-Za-z0-9_.-]+$` (they become wav file names) |
| `image` | file in `screenshots/` (or absolute path). One scene = one screenshot; reuse a screenshot across scenes if you need to |
| `clip` | instead of `image`: `{"src": "demo.mp4", "from": 0, "to": 4, "width": 1920, "height": 1080}` - a short real clip (loading state, drag-drop), muted, trimmed in seconds |
| `chapter` | chapter id; defaults to the previous scene's |
| `sentences` | `caption` = exact on-screen text (correct spelling/brand casing). `say` = what the voice gets (optional; default = caption with pronunciation table applied). **One sentence per entry, <= ~25 words.** Omit for a silent scene; then use `seconds` |
| `seconds` | duration of a scene with no sentences (default `pacing.hold`; for clips default = clip length) |
| `transition` | how this scene arrives: `auto` (push when the chapter changes, else crossfade), `crossfade` (same page, new state), `push` (navigated to a different page), `none` |
| `chip` | pill at the bottom of the card for the whole scene: breadcrumbs ("Settings > Integrations"), key claims, recommended values |
| `chips` | several timed pills: `[{"text": "...", "t0": 1.0, "t1": 3.5}]` (seconds from scene start) |

### focus: zoom + highlight + cursor
```json
{ "on": "New report", "x": 0.82, "y": 0.016, "w": 0.15, "h": 0.055, "zoom": 1.7, "hold": 2.4, "click": true }
```
| Key | Default | Notes |
|---|---|---|
| `on` | - | phrase from the scene's captions; the move starts 0.45 s before it is spoken so the zoom lands as the word is said. Case/punctuation-insensitive; a partial word matches as a fallback (warning if nothing matches) |
| `t` | scene lead | alternative to `on`: seconds from scene start when the zoom move begins |
| `x,y,w,h` | required | target box. `w,h` > 0 draws the highlight rectangle; give only `x,y` to zoom without a box |
| `zoom` | 1.6 | 1.3-1.9 works; the view is clamped so it never leaves the screenshot |
| `hold` | 2.4 | seconds to stay zoomed before easing back (0.7 s in/out). Consecutive focuses hand off smoothly |
| `click` | false | cursor glides to the box (curved path), press + ripple when the zoom lands |
| `cursor` | false | show the cursor moving there without a click |
| `highlight` | true if w,h > 0 | `false` zooms without the box |
The cursor carries over between scenes (it continues from where the previous scene left it). A scene without `click`/`cursor` focuses shows no cursor.
Pick targets from the narration: what the sentence is *about*. Check that the zoomed view does not cut a text label in half.

### blur: privacy
`"blur": [{"x": 0, "y": 0, "w": 0.16, "h": 1}]` - frosted strip over names, emails, other-project sidebars, client files. The boxes follow the zoom.
For recurring regions list them in every scene that shows them.

### callouts: pop a region forward
`"callouts": [{"t": 1.2, "x": 0.59, "y": 0.62, "w": 0.39, "h": 0.32, "scale": 1.12, "hold": 2.0}]` - a cropped copy of the region lifts off the page with a shadow.
Good for a number, a warning, a result card.

### type: animate text into an input
`"type": [{"t": 1.0, "x": 0.2, "y": 0.5, "w": 0.4, "h": 0.06, "text": "team@company.com", "fill": "#ffffff", "color": "#111827", "size": 26}]`
Draws a filled box (use the field's background colour) and types the text with a caret. Use only when the screenshot shows the empty field.

## Timing rules (what build_timeline.py does)
- scene = lead 0.35 s + sum(sentence clips) + 0.25 s between sentences + tail 0.5 s (first lead 0.6 s, last tail 1.0 s). A script tweak re-times everything.
- Transitions overlap the tail/lead padding (0.3 s crossfade, 0.35 s push), never the speech. Narration is assembled sample-accurately into one track,
  high-passed and loudness-normalised to -16 LUFS.
- Captions: sentences over 66 characters are split into chunks at commas/conjunctions; the spoken word is accent-coloured; word display is capped at 0.5 s.
  Word times come from faster-whisper when installed, otherwise from character counts over the clip's speech region.
