# awesome-product-demo-video

A Claude skill that turns **screenshots + an optional script** into a polished, enterprise-ready **product demo video**: narrated, captioned,
with smooth zooms, a moving cursor, step tracker and a branded intro/outro. No screen recording needed.

- **Bring a script or let Claude write it** from your screenshots and a few instructions.
- **Brand and theme detected automatically** from the screenshots and logo (accent, light/dark, fonts, logo plate).
- **Free, offline voiceover**: NVIDIA MagpieTTS on your own GPU (one-click Windows setup), with an `edge-tts` fallback or your own recordings.
- **Rendered with [Remotion](https://www.remotion.dev)**: data-driven, so a new video is a folder and a `manifest.json`, never new code.
- **Verified**: duration, resolution, audio sync, contact-sheet review and optional transcript check.

## Install
Copy the `product-demo-video/` folder into your skills directory (e.g. `~/.claude/skills/product-demo-video/`), then ask Claude:
> Make a product demo video from the screenshots in `./shots`. Audience: IT admins. Keep it under 2 minutes.

or, with your own script: *"Make a demo video from these screenshots and this script."*

## Requirements
Node.js 18+, Python 3.9+ (`pip install pillow numpy`), ffmpeg. Optional: `faster-whisper` (tighter caption sync), NVIDIA GPU + Windows for the local voice
(`product-demo-video/assets/tts/README.md`), or `pip install edge-tts` for the fallback voice.

## Try it without any product
`product-demo-video/examples/lumina/` has five fictional screenshots, a script and a complete manifest.

## Layout
```
product-demo-video/
  SKILL.md                 workflow Claude follows
  scripts/                 project setup, brand extraction, script parsing, voice jobs, timeline build, render, verify
  assets/remotion-template/ the Remotion project
  assets/tts/              start_voice_server.bat, voice_server.py, requirements (local text-to-speech)
  references/              manifest schema, script writing, design, voice, render/verify, environments
  examples/lumina/         sample inputs
```

## Notes
- Output is 1920x1080 (16:9). Vertical/square canvases are not supported yet.
- Fonts are installed from `@fontsource` packages (SIL Open Font License). The MagpieTTS model has its own license: check its model card for commercial use.
- Screenshots and scripts you supply stay on your machine; nothing is uploaded by the scripts (edge-tts, if you choose it, sends text to Microsoft's service).

License: MIT
