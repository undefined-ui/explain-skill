"""Shared locations for the video toolchain. Standard library only.

Everything heavy (the Python 3.12 venv, voice models) lives outside the skill folder,
so a skill update or a plugin reinstall does not throw it away:

    EXPLAIN_HOME (default ~/.cache/explain-skill)
      venv/            Manim, Kokoro, Piper, soundfile
      models/kokoro/   kokoro-v1.0.int8.onnx, voices-v1.0.bin
      models/piper/    <voice>.onnx + <voice>.onnx.json, downloaded on first use
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

HOME = Path(os.environ.get("EXPLAIN_HOME", Path.home() / ".cache" / "explain-skill"))
VENV = HOME / "venv"
MODELS = HOME / "models"
KOKORO_DIR = MODELS / "kokoro"
PIPER_DIR = MODELS / "piper"
SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent

PY_VERSION = "3.12"
KOKORO_FILES = {
    "kokoro-v1.0.int8.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def find_uv() -> str | None:
    """uv sets $UV inside `uv run`; otherwise look on PATH and in the default install dir."""
    for cand in (os.environ.get("UV"), shutil.which("uv")):
        if cand and Path(cand).exists():
            return cand
    local = Path.home() / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
    return str(local) if local.exists() else None


def kokoro_ready() -> bool:
    return all((KOKORO_DIR / name).exists() for name in KOKORO_FILES)
