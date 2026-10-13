#!/usr/bin/env python3
"""Local voice server for product-demo-video: NVIDIA MagpieTTS on your GPU, driven by Claude (or any script).

Run it once and leave it open:
    python voice_server.py --folder C:\\path\\to\\voice-data          # folder mode (connect that folder to Claude)
    python voice_server.py --folder C:\\path\\to\\voice-data --http   # also serve HTTP on 127.0.0.1:8765 (token protected)

Folder mode: Claude drops  <folder>/jobs/<name>.json  and reads  <folder>/results/<name>/  (wavs + durations.json + status.json).
Job file: {"job": "narration", "voice": "Aria", "chunks": [{"id": "s001", "text": "Hello."}, ...]}
HTTP mode: GET /health, POST /tts {"text","voice"} -> audio/wav, POST /jobs (same body as a job file), GET /jobs/<name>, GET /files/<name>/<file>.
Every HTTP request needs the header  Authorization: Bearer <token>  (the token is printed at start-up).
"""
import argparse, importlib.machinery, io, json, os, pathlib, re, secrets, shutil, sys, threading, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

def _check_deps(mock):
    import importlib.util as u
    need = ["numpy", "soundfile"] + ([] if mock else ["torch", "nemo", "kaldialign"])
    missing = [m for m in need if u.find_spec(m) is None]
    if missing:
        sys.exit(
            "\nMissing Python packages: " + ", ".join(missing) + "\n"
            "You are running: " + sys.executable + "  (Python " + sys.version.split()[0] + ")\n\n"
            "Install them in a Python 3.12 environment, then run this script again from that environment:\n"
            "Easiest: double-click start_voice_server.bat, which sets all of this up for you.\n"
        )


_check_deps("--mock" in sys.argv)


def _stub_missing_japanese():
    """pyopenjtalk (Japanese G2P) has no Windows wheel but MagpieTTS imports it while loading its config.
    English never touches it, so a stand-in module is enough."""
    import importlib.util, types
    if importlib.util.find_spec("pyopenjtalk") is None:
        m = types.ModuleType("pyopenjtalk")
        m.__spec__ = importlib.machinery.ModuleSpec("pyopenjtalk", None) if hasattr(importlib, "machinery") else None

        def _na(*a, **k):
            raise RuntimeError("Japanese text is not supported in this install")

        def _ga(name):
            if name.startswith("__"):
                raise AttributeError(name)
            return _na
        m.__getattr__ = _ga
        sys.modules["pyopenjtalk"] = m


if "--mock" not in sys.argv:
    _stub_missing_japanese()
import numpy as np, soundfile as sf  # noqa: E402

VOICES = {"Aria": 0, "Jason": 1, "John": 2, "Leo": 3, "Sofia": 4}  # indices from the model card
# Spoken forms for terms the model reads badly. Built-in list is generic; add your product's terms in <folder>/pronunciations.json,
# e.g. {"Acme": "Ack me", "SSO": "S S O"}. (The skill's scripts already apply pronunciations when they build the job, so this is a safety net.)
RESPELL = [("ChatGPT", "Chat G P T"), ("MCP", "M C P"), ("URL", "U R L"), ("PDF", "P D F"), ("API", "A P I"), ("SSO", "S S O"), ("5.5", "five point five")]
SAFE = re.compile(r"^[A-Za-z0-9_.\-]+$")


def load_extra_pronunciations(folder):
    f = pathlib.Path(folder) / "pronunciations.json"
    if f.exists():
        try:
            RESPELL[:0] = list(json.loads(f.read_text(encoding="utf-8")).items())  # user terms first
            print(f"loaded {len(RESPELL)} pronunciation rules (incl. {f.name})", flush=True)
        except Exception as e:  # noqa: BLE001
            print("could not read", f, e, flush=True)


def respell(t):
    for a, b in RESPELL:  # whole-word only, so 'API' never rewrites the inside of 'RAPID'
        t = re.sub(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])", b, t)
    return t


class Engine:
    """Loads MagpieTTS once; one synthesis at a time (GPU lock). --mock makes tones so the plumbing can be tested without a model."""

    def __init__(self, mock=False):
        self.mock, self.lock, self.sr, self.device = mock, threading.Lock(), 22050, "mock"
        if mock:
            return
        import torch
        from nemo.collections.tts.models import MagpieTTSModel
        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cpu":
            print("WARNING: CUDA not available - running on CPU, ~16x slower than real time.", flush=True)
        m = MagpieTTSModel.from_pretrained("nvidia/magpie_tts_multilingual_357m")
        self.model = m.to(self.device).eval()
        self.sr = int(getattr(m, "output_sample_rate", 22050))

    def info(self):
        gpu = None
        if not self.mock and self.device == "cuda":
            gpu = self.torch.cuda.get_device_name(0)
        return {"ok": True, "device": self.device, "gpu": gpu, "sample_rate": self.sr, "voices": list(VOICES)}

    def synth(self, text, voice):
        if voice not in VOICES:
            raise ValueError(f"unknown voice {voice!r}; choose from {list(VOICES)}")
        with self.lock:
            if self.mock:
                n = int(self.sr * max(0.4, 0.07 * len(text)))
                t = np.arange(n) / self.sr
                return (0.2 * np.sin(2 * np.pi * (180 + 40 * VOICES[voice]) * t)).astype(np.float32), self.sr
            with self.torch.no_grad():
                audio, n = self.model.do_tts(respell(text), language="en", apply_TN=False, speaker_index=VOICES[voice])
            return audio[0].float().cpu().numpy()[: int(n[0])], self.sr


def write_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, path)  # atomic, so a syncing folder never exposes half a file


def run_job(engine, outdir, job):
    outdir.mkdir(parents=True, exist_ok=True)
    chunks, voice = job["chunks"], job.get("voice", "Aria")
    status = {"state": "running", "done": 0, "total": len(chunks), "voice": voice, "started": time.time()}
    write_json(outdir / "status.json", status)
    durs = {}
    try:
        for i, c in enumerate(chunks, 1):
            if not SAFE.match(str(c["id"])):
                raise ValueError(f"bad chunk id {c['id']!r}")
            f = outdir / f"{c['id']}.wav"
            if f.exists():  # resumable
                durs[c["id"]] = round(sf.info(f).duration, 3)
            else:
                a, sr = engine.synth(c["text"], voice)
                sf.write(f, a, sr, subtype="PCM_16")
                durs[c["id"]] = round(len(a) / sr, 3)
            status.update(done=i)
            write_json(outdir / "status.json", status)
        write_json(outdir / "durations.json", durs)
        status.update(state="done", finished=time.time())
    except Exception:
        status.update(state="error", error=traceback.format_exc())
    write_json(outdir / "status.json", status)
    return status


def watch_folder(engine, root):
    jobs, results = root / "jobs", root / "results"
    (jobs / "done").mkdir(parents=True, exist_ok=True)
    results.mkdir(exist_ok=True)
    print(f"watching {jobs} - waiting for jobs...", flush=True)
    while True:
        for p in sorted(jobs.glob("*.json")):
            if time.time() - p.stat().st_mtime < 2:
                continue  # still being written
            try:
                job = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            name = str(job.get("job") or p.stem)
            if not SAFE.match(name):
                print("skipping job with unsafe name", name)
                shutil.move(str(p), str(jobs / "done" / (p.stem + ".rejected.json")))
                continue
            print(f"job {name}: {len(job['chunks'])} chunks, voice {job.get('voice', 'Aria')}", flush=True)
            st = run_job(engine, results / name, job)
            print(f"job {name}: {st['state']}", flush=True)
            shutil.move(str(p), str(jobs / "done" / p.name))
        time.sleep(1)


def make_handler(engine, token, outroot):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _auth(self):
            if self.headers.get("Authorization", "") != f"Bearer {token}":
                self._send(401, {"error": "missing or wrong bearer token"})
                return False
            return True

        def do_GET(self):
            if not self._auth():
                return
            parts = self.path.strip("/").split("/")
            if parts == ["health"]:
                return self._send(200, engine.info())
            if len(parts) == 2 and parts[0] == "jobs" and SAFE.match(parts[1]):
                f = outroot / parts[1] / "status.json"
                return self._send(200, f.read_bytes()) if f.exists() else self._send(404, {"error": "no such job"})
            if len(parts) == 3 and parts[0] == "files" and SAFE.match(parts[1]) and SAFE.match(parts[2]):
                f = outroot / parts[1] / parts[2]
                if f.exists():
                    ct = "audio/wav" if f.suffix == ".wav" else "application/json"
                    return self._send(200, f.read_bytes(), ct)
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._auth():
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
                if self.path == "/tts":
                    a, sr = engine.synth(body["text"], body.get("voice", "Aria"))
                    buf = io.BytesIO()
                    sf.write(buf, a, sr, format="WAV", subtype="PCM_16")
                    return self._send(200, buf.getvalue(), "audio/wav")
                if self.path == "/jobs":
                    name = str(body.get("job") or f"job{int(time.time())}")
                    if not SAFE.match(name):
                        return self._send(400, {"error": "bad job name"})
                    threading.Thread(target=run_job, args=(engine, outroot / name, body), daemon=True).start()
                    return self._send(202, {"job": name, "status": f"/jobs/{name}"})
            except Exception as e:
                return self._send(400, {"error": str(e)})
            self._send(404, {"error": "not found"})

    return H


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", help="shared folder for jobs/ and results/ (folder mode)")
    ap.add_argument("--http", action="store_true", help="also serve HTTP (token protected)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--token", default=os.environ.get("VOICE_TOKEN"))
    ap.add_argument("--mock", action="store_true", help="test mode: tones instead of the model")
    a = ap.parse_args()
    if not a.folder and not a.http:
        ap.error("give --folder and/or --http")
    t0 = time.time()
    engine = Engine(mock=a.mock)
    print(f"engine ready on {engine.device} in {time.time() - t0:.0f}s", flush=True)
    root = pathlib.Path(a.folder).expanduser() if a.folder else pathlib.Path("voice_work")
    if a.http:
        token = a.token or secrets.token_urlsafe(16)
        outroot = root / "results"
        outroot.mkdir(parents=True, exist_ok=True)
        srv = ThreadingHTTPServer((a.host, a.port), make_handler(engine, token, outroot))
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        print(f"HTTP on http://{a.host}:{a.port}   token: {token}", flush=True)
        print(f"  test:   curl -H \"Authorization: Bearer {token}\" http://{a.host}:{a.port}/health", flush=True)
        print(f"  tunnel: cloudflared tunnel --url http://{a.host}:{a.port}   (share the URL AND the token with Claude)", flush=True)
    if a.folder:
        load_extra_pronunciations(root)
        watch_folder(engine, root)
    else:
        while True:
            time.sleep(3600)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
