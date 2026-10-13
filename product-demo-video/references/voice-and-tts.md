# Voiceover

## Engines
| Engine | Where | Quality | Setup |
|---|---|---|---|
| **MagpieTTS local server** (default) | NVIDIA GPU on the user's Windows PC | natural, 5 voices, free, offline | `assets/tts/start_voice_server.bat` (one time, ~5 GB, 10-20 min) |
| **edge-tts** (fallback) | any OS, internet | good | `pip install edge-tts`; `scripts/tts_edge.py` |
| **Their own recordings** | - | whatever they record | one 16-bit PCM wav per sentence id in `<video>/audio/` |
| **Silent** | - | captions + estimated timing (0.4 s/word) | `build_timeline.py --silent` |

All engines end in the same place: `<video>/audio/<sentence id>.wav` + `<video>/audio/durations.json`.

## Local server contract (folder mode)
`assets/tts/` holds `start_voice_server.bat` (creates a private Python 3.12 env, installs pinned packages + CUDA PyTorch, starts the server) and `voice_server.py`.
It watches `<tts folder>/voice-data/jobs/` and writes `voice-data/results/<job>/`.
- Job: `{"job": "<name>", "voice": "Sofia", "chunks": [{"id": "s01a", "text": "..."}]}` - names/ids match `^[A-Za-z0-9_.-]+$`.
- Output per chunk: `<id>.wav` (22.05 kHz mono PCM16). `status.json` (`state`: running/done/error + traceback). `durations.json` (only when finished).
- The job file moves to `jobs/done/` when finished. Speed ~1.3x the audio length (190 s for ~140 s of speech); a 4-word test returns in seconds.
- **Existing wavs are skipped**, so changed text needs a NEW job name. `scripts/voice_job.py submit` refuses to reuse a name.
- Optional `voice-data/pronunciations.json` ({"Acme": "Ack me"}) is loaded at server start (restart to pick up changes).

## Commands (`scripts/voice_job.py`, standard library only)
```
voice_job.py lint    --manifest <video>/manifest.json
voice_job.py submit  --manifest <video>/manifest.json --root <tts folder>/voice-data --job <video>_v1 [--voice Sofia]
voice_job.py wait    --root <tts folder>/voice-data --job <video>_v1          # repeat until "done" (each call <= ~170 s)
voice_job.py collect --root <tts folder>/voice-data --job <video>_v1 --audio-dir <video>/audio
```
Fixing lines: edit the caption/`say` in the manifest, then `submit --only s03a,s05b --job <video>_fix01`, `wait`, `collect` (collect overwrites those wavs), `build_timeline.py`, re-render.
Exit codes of `wait`: 0 done, 2 server error (traceback printed), 3 not finished / server probably not running (no status after 30 s).

## Pronunciation
The voice reads written text; fix what it gets wrong *in the spoken text only* so captions stay correct.
- Spell out acronyms letter by letter with spaces: "A P I", "S S O", "S Q L" (the generic table covers API, SSO, UI, UX, URL, PDF, CSV, MCP, SDK, CRM, KPI, AI, ChatGPT).
- Brand names the model mangles: respell phonetically ("Acme" -> "Ack me"; "Figma" is usually fine). Put them in `pronunciations.json` next to the manifest or in the manifest's `pronunciations`.
- Numbers, versions, units, dates: write as spoken ("version two point one", "twenty-eight percent", "October third").
- Avoid parentheses, slashes, underscores, `>`; say "then" for breadcrumbs. `lint` flags these.
- You cannot hear the audio. Run `verify_video.py --transcribe` (faster-whisper) to compare what was said with the text, say so honestly, and ask the user to flag lines that sound wrong.
  Whisper itself mishears brand names, so a low score on a brand term is a prompt to listen, not proof of a bad line.

## Voice choice
Default Sofia (clear, warm). Aria, Jason, John, Leo are alternatives. To compare, submit the same two sentences under different `--voice` values with different job names and let the user pick.

## Timing fallbacks
- `build_timeline.py` reads real clip lengths, so scene durations follow the audio automatically.
- Without faster-whisper, caption word timing is proportional to character count within the clip's detected speech region: fine for sentences under ~25 words.
