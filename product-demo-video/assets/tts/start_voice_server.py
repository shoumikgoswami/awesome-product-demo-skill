#!/usr/bin/env python3
"""Cross-platform launcher for the local MagpieTTS voice server (Windows or Linux, NVIDIA GPU required).

First run: creates a private Python 3.12 venv, installs pinned packages + a CUDA build of PyTorch.
Later runs: just start voice_server.py. Any Python 3.8+ can run this file; the venv uses 3.12.

    python start_voice_server.py            # or start_voice_server.bat / start_voice_server.sh
Env: VOICE_ENV_DIR=<path> places/reuses the venv elsewhere.
"""
import os, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
WIN = os.name == "nt"
MARKER_NAME = "setup_done_v1.txt"
TORCH_BUILDS = ("cu128", "cu126", "cu124")
TORCH_CHECK = ("import torch,torchvision,torchaudio;from torchvision.ops import nms;"
               "print('torch',torch.__version__,'torchvision',torchvision.__version__,'CUDA',torch.cuda.is_available());"
               "import sys;sys.exit(0 if torch.cuda.is_available() else 1)")


def default_env_dir():
    if os.environ.get("VOICE_ENV_DIR"):
        return pathlib.Path(os.environ["VOICE_ENV_DIR"]).expanduser()
    if WIN:
        return pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "product-demo-voice-env"
    base = pathlib.Path(os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share"))
    return base / "product-demo-voice-env"


ENV = default_env_dir()
PY = ENV / ("Scripts/python.exe" if WIN else "bin/python")


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], **kw).returncode == 0


def die(msg):
    print("\n" + msg)
    sys.exit(1)


def find_python312():
    """Return the path of a Python 3.12 interpreter, or None."""
    candidates = ([["py", "-3.12"]] if WIN else []) + [["python3.12"], ["python3"], ["python"]]
    for c in candidates:
        if not shutil.which(c[0]):
            continue
        try:
            out = subprocess.run(c + ["-c", "import sys;print(sys.version_info[:2]==(3,12), sys.executable)"],
                                 capture_output=True, text=True).stdout.split(None, 1)
        except OSError:
            continue
        if len(out) == 2 and out[0] == "True":
            return out[1].strip()
    if WIN:
        p = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Python/Python312/python.exe"
        if not p.exists():
            print("Python 3.12 not found - installing it with winget...")
            run(["winget", "install", "-e", "--id", "Python.Python.3.12", "--silent",
                 "--accept-package-agreements", "--accept-source-agreements"])
        if p.exists():
            return str(p)
    return None


def has_nvidia():
    return bool(shutil.which("nvidia-smi")) and run(["nvidia-smi"], capture_output=True)


def install_torch():
    for build in TORCH_BUILDS:
        print(f"\nInstalling PyTorch with CUDA build {build} ...")
        cmd = [PY, "-m", "pip", "install", "torch", "torchvision", "torchaudio",
               "--index-url", f"https://download.pytorch.org/whl/{build}", "--force-reinstall"]
        if WIN:  # Windows wheels bundle CUDA; Linux wheels need their nvidia-* dependencies
            cmd.append("--no-deps")
        run(cmd)
        if run([PY, "-c", TORCH_CHECK]):
            return True
    return False


def setup():
    print("=" * 60)
    print(" First-time setup (about 10-20 minutes, downloads ~5 GB).")
    print(" It only happens once. Please keep this window open.")
    print("=" * 60)
    if not has_nvidia():
        die("No working NVIDIA GPU/driver found (nvidia-smi failed).\n"
            "The MagpieTTS voice server needs an NVIDIA GPU (Windows or Linux).\n"
            "On macOS, AMD or CPU-only machines use the fallback instead:\n"
            "  scripts/tts_edge.py (pip install edge-tts), or bring your own <sentence id>.wav files.\n"
            "See assets/tts/README.md.")
    base = find_python312()
    if not base:
        hint = ("Install Python 3.12 from python.org (tick 'Add to PATH')." if WIN else
                "Install Python 3.12 with its venv module, e.g. 'sudo apt install python3.12 python3.12-venv' "
                "or use pyenv/uv, then run this again.")
        die("Could not find or install Python 3.12. " + hint)
    print("Using Python:", base)
    if not PY.exists():
        print(f"Creating environment in {ENV} ...")
        if not run([base, "-m", "venv", ENV]):
            die("Could not create the virtual environment (Debian/Ubuntu: sudo apt install python3.12-venv).")
    if not run([PY, "-m", "pip", "install", "--upgrade", "pip"]):
        die("pip upgrade failed.")
    failed = "Setup stopped because a step failed. Copy the last lines above and send them to Claude."
    print("\nInstalling speech packages...")
    if not run([PY, "-m", "pip", "install", "-r", HERE / "requirements.txt",
                "--no-binary", "jieba,wget,antlr4-python3-runtime"]):
        die(failed)
    if not run([PY, "-m", "pip", "install", "nemo-toolkit==3.0.0", "--no-deps"]):
        die(failed)
    if not install_torch():
        die("PyTorch was installed but cannot see the GPU. Update the NVIDIA driver, then run this again.\n"
            f"(To retry from scratch, delete the folder {ENV})")
    (ENV / MARKER_NAME).write_text("done")
    print("\nSetup finished.")


def main():
    os.environ.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
    if not (ENV / MARKER_NAME).exists():
        setup()
    if not run([PY, "-c", TORCH_CHECK], capture_output=True):
        print("\nPyTorch needs repairing - reinstalling it, one time only...")
        if not install_torch():
            die("PyTorch cannot see the GPU. Update the NVIDIA driver, then run this again.\n"
                f"(To retry from scratch, delete the folder {ENV})")
    print("\nStarting the voice server. The first start also downloads the voice model.")
    print("Leave this window open. Wait for the line that says it is watching for jobs.\n")
    code = subprocess.call([str(PY), str(HERE / "voice_server.py"), "--folder", str(HERE / "voice-data")])
    print("\nThe server has stopped. Copy any error text above and send it to Claude.")
    sys.exit(code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
