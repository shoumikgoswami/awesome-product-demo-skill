---
name: product-demo-video
description: Create polished, enterprise-ready product demo videos from screenshots plus an optional script, with no screen recording. Auto-detects brand colours and theme, writes the narration if none is given, generates a free local text-to-speech voiceover, and renders animated zooms, cursor clicks, captions, step tracker and a branded intro/outro with Remotion. Use for product demos, walkthroughs, feature tours, onboarding or tutorial videos.
---

# Product demo video

Turns a folder of **screenshots** (+ optional **script** or **instructions**) into a 1080p product demo video: narrated, captioned, with
smooth zooms, a moving cursor, step tracker and a branded intro/outro. Brand colours and light/dark styling are detected from the
screenshots and logo. Everything is data-driven: a new video = a new folder and a `manifest.json`, never new code.

Stack: Remotion 4 (React renders the frames), ffmpeg, Pillow/numpy, a local MagpieTTS voice server (free, offline, NVIDIA GPU) with an
`edge-tts` fallback, optional faster-whisper for tighter caption timing. All paths below are relative to this skill folder.

## Two ways to start
| Mode | The user gives | You do |
|---|---|---|
| **A. Script provided** | screenshots + a narration script | `parse_script.py` maps script scenes to screenshots, splits sentences. Never rewrite their words except for TTS pronunciation (`say`). |
| **B. Script generated** | screenshots + instructions (audience, goal, tone, length, key facts) | Look at every screenshot, write the script per `references/script-writing.md`, show it, then continue. |

Optional in both: logo, brand hex colours or a product URL, music, voice choice, target length, pins like "slide 4 is the settings page".

## Inputs: ask once, only for what is missing
Screenshots are the one hard requirement. Ask a single short message for anything else that changes the result (mode B: audience, goal,
length, facts you cannot see; either mode: logo, product name if not visible). **Never wait on optional items: pick defaults and say
which.** All text on screen (intro, outro, chips, captions) comes from the script, the screenshots or text the user supplied.
**Never invent claims, prices, customer names, statistics or feature names.**

## Where things run
Read `references/environments.md` first if you are not sure. In short:
- **Local** (Claude Code on the user's machine): run the scripts directly; render locally; the voice server runs on the same machine.
- **Cloud workspace linked to the user's PC**: files and the GPU voice server live on the PC; reach them with the device tools
  (`device_bash`, `device_stage_files`, `device_commit_files`), render in the workspace, copy results back. Details in the reference.

## Workflow (make a task list; the last task is verification)

### 1. One-time setup
- `python scripts/setup_renderer.py --dest renderer` (Node 18+, ffmpeg; installs Remotion + bundled fonts; safe to re-run).
- `pip install pillow numpy`; optional `pip install faster-whisper` (caption sync; works without).
- Voice: confirm the voice server is running (step 5) or choose the fallback. Do not start the 5 GB install unprompted: explain it
  (`assets/tts/README.md`) and let the user run `start_voice_server.bat` (Windows) or `start_voice_server.sh` (Linux).

### 2. Create the project and inspect (silent, then one short message)
`python scripts/new_project.py --name <video> --screens <folder> [--script s.txt] [--logo logo.png] [--product "<Name>"] --root <workdir>`
creates `<video>/` with copies of the screenshots (originals are never edited), `theme.json` + `brand-swatches.png`,
`inspect/contact-sheet.png` + `inspect/grid/*.png` and a `manifest.json` skeleton. Then **look** at the contact sheet, every screenshot
and the swatches. Check:
- **Privacy**: names, emails, client/company names, file paths, tokens, URLs with ids, other-project sidebars, notification toasts.
  Plan `blur` boxes (see manifest reference) or tell the user what to retake. Tell them what you found in the first message.
- **Quality**: low resolution (<1280 px), mixed sizes, cropped browser chrome, test data that looks fake.
- **Brand**: do the swatches match what you see in the product and logo? See `references/brand-and-design.md` to override.

### 3. Theme
Auto-detection is a heuristic; sanity-check `brand-swatches.png`. If `_meta.confidence` is `low` or the accent is wrong, re-run
`extract_brand.py` with `--primary "#hex"` / `--base` / `--mode light|dark` / `--font ...`, or edit `theme.json`. If the user gave a
URL or brand colours, use those. Tell the user which accent, mode and font you chose in one line.

### 4. Script and manifest
- **Mode A**: `parse_script.py` already produced scenes; verify the mapping table it printed (scene -> screenshot) and fix with `[img: file]` pins or by editing the manifest.
- **Mode B**: follow `references/script-writing.md`. Show the script (or a tight summary of it) to the user before voicing when they are present; if they said "just do it" or you are unattended, continue and flag it in the final message.
- Complete `manifest.json` (full schema: `references/manifest-reference.md`): chapters (3-5 steps, plus Overview), `focus` entries with coordinates read
  off `inspect/grid/*.png`, `chip` breadcrumbs, `blur` boxes, intro/outro copy. Use `"on": "<phrase>"` so zooms follow the narration
  automatically. One sentence per entry (<= 25 words); `caption` = correct on-screen spelling.

### 5. Voiceover (`references/voice-and-tts.md`)
1. `python scripts/voice_job.py lint --manifest <video>/manifest.json` - fix risky terms (acronyms need spaces: "A P I"); add product terms to `pronunciations.json`.
2. `submit --job <video>_v1` -> `wait` (poll until `done`) -> `collect --audio-dir <video>/audio`.
3. If nothing starts within ~30 s the server is not running: tell the user to start `start_voice_server.bat` (Windows) or `start_voice_server.sh` (Linux); do not wait indefinitely.
4. No GPU: `scripts/tts_edge.py`; user's own recordings: drop `<sentence id>.wav` files in `<video>/audio/`; no voice: `--silent` (captions only).
5. A corrected line always goes in a **new** job name (the server skips existing wavs). You cannot listen: say so, and ask the user to flag mispronunciations.

### 6. Build, then look at stills
`python scripts/build_timeline.py --video-dir <video> --template renderer` -> reads manifest + audio, writes timeline, narration track and copies
assets to `renderer/public/<video>/`. Read every WARNING. Then `python scripts/render.py stills --template renderer --name <video> --out <video>/stills`
and **view the contact sheet and the individual stills** (zooms, cursor on target, no text cut in half, blur covers the right area, chips
readable, captions fit). Fix the manifest, rebuild (seconds), re-check. Do not full-render until the stills are right.

### 7. Render
`python scripts/render.py video --template renderer --name <video> --out <video>/<video>.mp4` (about 7 fps on 2 CPU cores for
screenshot scenes: a 3-minute video takes ~15 min; tell the user the ETA first). Run long renders in the background with a log file and poll.

### 8. Verify (never skip)
`python scripts/verify_video.py --video <mp4> --template renderer --name <video> --manifest <video>/manifest.json [--transcribe]` then view its contact sheet.
Confirm: duration/resolution/audio PASS, first speech at the expected time, nothing clipped, no personal data visible, brand spelled correctly in captions.

### 9. Deliver
Send the MP4 (and manifest if useful). Keep the reply short: what it is, then only decisions the user must make: lines the voice may have
mispronounced, blurs applied, guessed zooms/theme, no music, low-res screenshots. Keep the project folder: **edits are cheap** (change a line ->
new voice job for that sentence -> `build_timeline.py` -> re-render; change a colour -> `theme.json` -> rebuild).

## Don'ts
- Don't invent product claims, prices, testimonials or feature names; use the script, the screenshots and supplied copy.
- Don't edit the user's original screenshots or script; work on copies.
- Don't reuse a voice job name or chunk id to change text. Don't send multi-sentence paragraphs as one chunk.
- Don't leave personal data, client names, emails or local paths unblurred without telling the user.
- Don't full-render before the stills look right. Don't wait on the voice server indefinitely.
- Don't claim you listened to the audio. Verification is by transcript and timing, plus the user's ear.
- Don't hand-edit the Remotion code for ordinary changes; everything visual is driven by `manifest.json` / `theme.json`. Edit `renderer/src/*` only for new design features (see `references/brand-and-design.md`).

## File map
- `scripts/` - `new_project.py`, `inspect_screens.py`, `extract_brand.py`, `parse_script.py`, `voice_job.py`, `tts_edge.py`, `build_timeline.py`, `render.py`, `verify_video.py`, `setup_renderer.py`
- `assets/remotion-template/` - the Remotion project (copied to `renderer/` by `setup_renderer.py`)
- `assets/tts/` - `start_voice_server.py` (+ `.bat`/`.sh` wrappers), `voice_server.py`, `requirements.txt`, README (local text-to-speech)
- `references/` - `manifest-reference.md`, `script-writing.md`, `brand-and-design.md`, `voice-and-tts.md`, `render-and-verify.md`, `environments.md`
- `examples/lumina/` - fictional product, 5 screenshots + a complete `manifest.json` to try the pipeline in minutes
