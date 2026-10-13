# Local voice server (free, offline text-to-speech)

Narration for the demo videos comes from **NVIDIA MagpieTTS** (`nvidia/magpie_tts_multilingual_357m`) running on your own GPU.
No API key, no per-minute cost, nothing leaves your machine. Five built-in voices: **Sofia** (default), Aria, Jason, John, Leo.

## Requirements
- **Windows 10/11 or Linux** with an **NVIDIA GPU** and a current driver (`nvidia-smi` must work). The Linux path is untested - please report issues.
- About **5 GB** of disk for the first-time install, 10-20 minutes, internet for that first run only
- Nothing else on Windows: the launcher installs Python 3.12 (via winget) if missing. On Linux install `python3.12` + `python3.12-venv` first.
- The launcher builds its own virtual environment (`%LOCALAPPDATA%\product-demo-voice-env` on Windows, `~/.local/share/product-demo-voice-env` on Linux),
  installs pinned packages and a CUDA build of PyTorch that works with your driver

## Use
1. **Windows:** double-click **`start_voice_server.bat`**. **Linux:** run `./start_voice_server.sh`. (Both just call `python start_voice_server.py`, which you can also run directly.) Leave the window open. First run = setup, later runs start in seconds
   (the model is downloaded on the first start, then cached).
2. Wait for the line `watching ...\voice-data\jobs - waiting for jobs...`
3. The skill (or you) drops job files into `voice-data\jobs\` and reads the results from `voice-data\results\<job>\`.

```
voice-data/
  jobs/<job>.json            <- written by scripts/voice_job.py (moved to jobs/done/ when finished)
  results/<job>/<id>.wav     <- 22.05 kHz mono PCM16, one per sentence
  results/<job>/durations.json   <- written when the job is finished
  results/<job>/status.json      <- state: running | done | error (with traceback)
  pronunciations.json        <- optional, your own spoken forms, e.g. {"Acme": "Ack me", "SSO": "S S O"}
```

Job file: `{"job": "my-video_v1", "voice": "Sofia", "chunks": [{"id": "s01a", "text": "One sentence."}, ...]}`

### Rules worth knowing
- **A chunk whose wav already exists in `results/<job>/` is skipped.** To change a line, submit it in a NEW job name.
- Keep each chunk to one sentence (<= ~25 words); the model is steadier and timings stay clean.
- Speed: roughly 1.3x the audio length on a recent GPU (about 190 s for 140 s of speech); the first job after start-up is slower.
- Expand abbreviations for the voice ("A P I", "S S O"); `pronunciations.json` and the skill's `voice_job.py lint` help.

### Options
- `set VOICE_ENV_DIR=C:\path\to\env` before launching reuses an existing environment instead of creating a new one.
- `python voice_server.py --folder voice-data --http` also serves a token-protected HTTP API on 127.0.0.1:8765.
- `python voice_server.py --folder voice-data --mock` makes tones instead of speech - for testing the plumbing without a GPU.

### No NVIDIA GPU (macOS, AMD, CPU-only)?
The launcher stops with a message in that case. Use the fallback `scripts/tts_edge.py` (Microsoft Edge neural voices via `pip install edge-tts`, needs internet),
or bring your own narration: put `<sentence id>.wav` files (16-bit PCM) into `<video>/audio/` and run `build_timeline.py` as usual.

### Troubleshooting
| Symptom | Fix |
|---|---|
| "nvidia-smi was not found" | Install/update the NVIDIA driver, run the launcher again |
| "PyTorch ... cannot see the GPU" | Update the driver; to start over delete the environment folder (see above) |
| Setup stops at a pip error | Copy the last lines of the window; re-run (setup resumes) |
| Jobs sit there and nothing happens | The window was closed - start the launcher again |
| A word is mispronounced | Add it to `pronunciations.json` (restart the server) or respell it in the script; re-voice that sentence in a new job |

Model: NVIDIA MagpieTTS Multilingual 357M - check its model card for the current license terms before commercial use.
