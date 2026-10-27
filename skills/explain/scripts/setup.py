#!/usr/bin/env python3
"""One-time setup for video mode: a Python 3.12 venv with Manim + local TTS, and the Kokoro voice model.

    uv run --no-project --python 3.12 setup.py      # what install.sh / install.ps1 run
    python setup.py --force                          # rebuild the venv
    python setup.py --skip-models                    # packages only

Needs uv (https://docs.astral.sh/uv/). Downloads about 400 MB in total. Safe to run again:
finished steps are skipped. Standard library only, so any Python 3.8+ can start it.
"""

from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import HOME, KOKORO_DIR, KOKORO_FILES, PY_VERSION, VENV, find_uv, venv_python  # noqa: E402

PACKAGES = ["manim>=0.19", "kokoro-onnx>=0.4", "piper-tts>=1.3", "soundfile>=0.12", "numpy"]
CHECK = "import manim, kokoro_onnx, piper, soundfile, av; print(manim.__version__)"


def step(msg: str) -> None:
    print(f"\n==> {msg}", flush=True)


def download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"    have {dest.name}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "explain-skill-setup"})
    with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done, last = 0, -1
        while chunk := r.read(1 << 20):
            f.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else -1
            if pct >= 0 and pct // 10 != last:
                last = pct // 10
                print(f"    {dest.name}: {pct}% of {total / 1e6:.0f} MB", flush=True)
    tmp.replace(dest)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="delete and rebuild the venv")
    ap.add_argument("--skip-models", action="store_true", help="do not download the Kokoro model")
    args = ap.parse_args()

    uv = find_uv()
    if not uv:
        print("uv is not installed. Install it, then run this again:\n"
              "  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
              "  Windows:     powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"", file=sys.stderr)
        return 1

    HOME.mkdir(parents=True, exist_ok=True)
    if args.force and VENV.exists():
        step(f"Removing {VENV}")
        shutil.rmtree(VENV)

    py = venv_python()
    if not py.exists():
        step(f"Creating Python {PY_VERSION} venv at {VENV}")
        subprocess.run([uv, "venv", "--python", PY_VERSION, str(VENV)], check=True)

    step("Installing Manim, Kokoro, Piper (first run takes a few minutes)")
    try:
        subprocess.run([uv, "pip", "install", "--python", str(py), *PACKAGES], check=True)
    except subprocess.CalledProcessError:
        if platform.system() == "Linux":
            print("\nOn Linux, Manim needs Cairo and Pango headers. Install them, then run this again:\n"
                  "  Debian/Ubuntu: sudo apt install build-essential python3-dev libcairo2-dev libpango1.0-dev pkg-config\n"
                  "  Fedora:        sudo dnf install cairo-devel pango-devel python3-devel", file=sys.stderr)
        raise

    if not args.skip_models:
        step("Downloading the Kokoro voice model (about 115 MB, free, runs locally)")
        for name, url in KOKORO_FILES.items():
            download(url, KOKORO_DIR / name)

    step("Checking the install")
    out = subprocess.run([str(py), "-c", CHECK], capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stderr, file=sys.stderr)
        return 1
    print(f"    manim {out.stdout.strip()} OK")

    print(f"\nVideo mode is ready.\n  Python: {py}\n  Data:   {HOME}")
    print("  Voice:  ElevenLabs if ELEVENLABS_API_KEY is set, else Kokoro (local). Russian and other languages: Piper (local).")
    if not shutil.which("latex"):
        print("  Note:   no LaTeX found. Scenes use Text() instead of MathTex(). Install TeX Live / MiKTeX for MathTex.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
