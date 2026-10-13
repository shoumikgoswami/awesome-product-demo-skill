# Where things run

The skill works in two setups. Decide which one you are in before touching files.

## 1. Local (Claude Code or any agent on the user's own machine)
- Run all scripts directly with `python`. The renderer folder, the video folders and the voice server's `voice-data/` are ordinary paths.
- The voice server runs on the same machine (NVIDIA GPU) or you use `tts_edge.py` / the user's own recordings.
- Render locally. The first render downloads Remotion's headless Chrome.
- Windows quoting: use the `render.py` wrapper rather than passing JSON to `npx` yourself; paths with spaces must be quoted.

## 2. Cloud workspace linked to the user's computer (Claude desktop app + device tools)
Typical situation: the agent's shell runs in a cloud Linux workspace (Node, ffmpeg, Chrome are there), while the screenshots and the GPU voice server live on the user's Windows PC.
- Files on the PC are reached with `device_list_dir`, `device_stage_files` (PC -> workspace, <= 50 files/call), `device_commit_files` (workspace -> PC, <= 30 MB/file) and, when present, `device_bash` (a shell on the PC scoped to the connected folders, mounted under `$HOME/mnt/<folder-name>`).
- **Stage only what a step needs.** Screenshots + logo + script go to the workspace; work there; commit the finished `manifest.json`, `theme.json`, audio and the MP4 back.
- **Voice**: the server on the PC watches `<tts folder>/voice-data/jobs/`. Write the job file with `voice_job.py submit` run through `device_bash` if Python exists on the PC, otherwise write the JSON by hand
  (contract in `voice-and-tts.md`) with `device_bash`. Poll `results/<job>/status.json` with short `sleep` loops. Then stage the wavs + `durations.json` into the workspace's `<video>/audio/`.
  If the PC has no Python on PATH, the Windows environment created by `start_voice_server.bat` has one at `%LOCALAPPDATA%\product-demo-voice-env\Scripts\python.exe`.
- **Deleting** on the PC is not allowed by default; never rely on deleting stale files (use new job names, new file names).
- **Large outputs**: an MP4 over 30 MB cannot be committed back in one piece; deliver it to the user directly (file download) and say where the project folder is.
- If no device tools are present the PC is not linked: ask the user to attach the screenshots (and script/logo) to the chat and do everything in the workspace. The voice step then needs `tts_edge.py`
  (internet) or their own recordings, or they run the voice server and send the wavs.

## Either way
- Never edit the originals; copy into the project folder.
- Keep the project folder (manifest, theme, audio, screenshots, renderer/public/<video>) so later edits are small.
- Say plainly what you could not do (e.g. could not listen to the voice, voice server not running) instead of papering over it.
