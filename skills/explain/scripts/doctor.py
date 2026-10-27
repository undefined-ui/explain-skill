#!/usr/bin/env python3
"""Report what the explain skill can do on this machine. Standard library only.

    python doctor.py

Prints the video Python path (use it as $PY), which voice engine `tts.py --engine auto`
will pick, and what is missing. Never prints API keys.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import HOME, PIPER_DIR, find_uv, kokoro_ready, venv_python  # noqa: E402


def main() -> int:
    py = venv_python()
    rows = []
    venv_ok = py.exists()
    imports_ok = False
    if venv_ok:
        r = subprocess.run([str(py), "-c", "import manim, kokoro_onnx, piper, soundfile; print(manim.__version__)"],
                           capture_output=True, text=True)
        imports_ok = r.returncode == 0
        rows.append(("video venv", f"OK, manim {r.stdout.strip()}" if imports_ok else "BROKEN, run setup.py --force"))
    else:
        rows.append(("video venv", "MISSING, run: uv run --no-project --python 3.12 scripts/setup.py"))

    has_key = bool(os.environ.get("ELEVENLABS_API_KEY"))
    rows.append(("ElevenLabs key", "set" if has_key else "not set (optional)"))
    rows.append(("Kokoro model", "OK" if kokoro_ready() else "missing (setup.py downloads it)"))
    piper_voices = sorted(p.stem for p in PIPER_DIR.glob("*.onnx")) if PIPER_DIR.exists() else []
    rows.append(("Piper voices", ", ".join(piper_voices) or "none yet (downloaded on first use)"))
    rows.append(("uv", find_uv() or "missing"))
    rows.append(("LaTeX", "yes, MathTex works" if shutil.which("latex") else "no, use Text() not MathTex()"))

    auto = "elevenlabs" if has_key else ("kokoro (en/es/fr/it/pt/hi/ja/zh) or piper (ru/uk/de/pl/...)"
                                         if kokoro_ready() else "none until setup.py runs")
    rows.append(("tts --engine auto", auto))

    width = max(len(k) for k, _ in rows)
    for k, v in rows:
        print(f"{k:<{width}}  {v}")
    print(f"\nPY={py}")
    print(f"EXPLAIN_HOME={HOME}")
    return 0 if (venv_ok and imports_ok) else 2


if __name__ == "__main__":
    sys.exit(main())
