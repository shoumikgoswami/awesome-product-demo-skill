# Build, render, verify

## Build the timeline
`python scripts/build_timeline.py --video-dir <video> --template renderer [--name <video>] [--silent] [--no-whisper]`
Writes `renderer/public/<name>/`: `timeline.json`, `props.json`, `narration.wav`, `images/`, logo, clips, music. Re-run after every manifest/theme/audio change (seconds).
Typical warnings and what to do:
| Warning | Meaning / fix |
|---|---|
| `focus 'x' has no x/y coordinates yet - skipped` | a zoom directive still needs coordinates: read them off `inspect/grid/` |
| `focus 'on': '...' not found in the caption text` | the phrase is not in that scene's captions; fix the phrase or use `t` |
| `focus box extends past the screenshot edge` / `outside 0-1` | coordinates are fractions, not pixels |
| `a focus move starts at Xs but the scene is only Ys long` | focus is too late for that scene; move it earlier or lengthen the scene |
| `faster-whisper not available` | captions timed by characters (fine); `pip install faster-whisper` for tighter sync |
| `chapter has no scenes` | remove it or assign scenes |
| `missing voice clips for: ...` | run the voice step, or pass `--silent` |

## Stills first
`python scripts/render.py stills --template renderer --name <video> --out <video>/stills` renders: intro mid/end, each scene's middle, every transition midpoint,
every zoom landing, outro. View `contact-sheet.png`, then any frame at full size that looks off. Checklist:
- Highlight box encloses the right element; the zoom view does not cut a label in half (adjust `x,y,w,h` or `zoom`).
- Cursor tip rests on the target, not covering its label.
- Blur boxes cover every personal item - also while zoomed in (the boxes follow the zoom).
- Chips readable and not covering the thing being discussed; captions fit on one or two lines; header text not truncated.
- Logo legible; accent colour reads against the background; intro headline highlight on the right words; outro URL correct.
- No fake-looking data (lorem ipsum, "test test"), no browser/OS chrome you did not intend to show.
Single frames: `render.py stills --frames 120,450` (frame numbers are global: intro frames come first).

## Full render
`python scripts/render.py video --template renderer --name <video> --out <video>/<video>.mp4 [--concurrency 2] [--crf 18] [--range 0-299]`
- Speed: ~7 fps on 2 CPU cores for screenshot scenes (a 42 s test took ~3 min). Estimate `totalFrames / 7` seconds, say it, then run in the background with a log and poll.
- `--range` renders a slice for a quick motion check.
- H.264 CRF 18 + AAC; 1920x1080. Typical size ~1 MB per 7 s. Over 30 MB: the file cannot be pushed through the device bridge in one piece - send it as a download instead and say so.
- Browser: Remotion downloads its own headless Chrome on first use. On restricted networks set `PRODUCT_DEMO_BROWSER=<path to chrome/headless_shell>`
  (Playwright's `/opt/pw-browsers` is auto-detected). Fonts are bundled, so nothing else touches the network.

## Verify
`python scripts/verify_video.py --video <mp4> --template renderer --name <video> --manifest <video>/manifest.json [--transcribe]`
Hard checks: duration == frames/fps (+-0.15 s), 1920x1080, audio stream present. Soft: first speech where the timeline says. Then view `verify/contact-sheet.png`.
`--transcribe` re-listens with faster-whisper and prints per-scene similarity to the spoken text.

## Troubleshooting
| Symptom | Cause / fix |
|---|---|
| Blank render, `Cannot load public/<name>/timeline.json` | run `build_timeline.py`; pass `--props=public/<name>/props.json` (render.py does) |
| Text in a fallback font | `npm run setup-fonts` in `renderer/`, or the theme font name is wrong (valid list in brand-and-design.md) |
| Image not shown | file name in the manifest differs (case, extension); `build_timeline.py` stops if it cannot find it |
| Zoom shows the blurred letterbox | very different aspect ratios in one set: retake to one size or accept letterbox |
| Captions drift from speech | install faster-whisper; or shorten sentences; confirm the wavs are the ones in the manifest |
| `backdrop-filter` blur missing | uncommon headless browsers; use Remotion's own Chrome download |
| Out of memory | lower `--concurrency` to 1 |
| `Failed to launch the browser process` / `spawn ... ENOENT` on Windows | The renderer folder path is too deep (Chrome ends up over the 260-character limit). Set it up in a short folder, e.g. `setup_renderer.py --dest C:\pdvenderer` |
