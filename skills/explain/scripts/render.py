#!/usr/bin/env python3
"""Render a narrated Manim scene to MP4, then save stills so you can check the frames.

    "$PY" render.py explainers/<slug>/scene.py                 # 1080p60, first Scene class in the file
    "$PY" render.py explainers/<slug>/scene.py --quality l     # fast 480p draft
    "$PY" render.py scene.py Explainer --stills 8 --open

Writes <slug>.mp4 (or <slug>-draft.mp4 for l/m quality), <slug>.srt, and stills/*.png next to scene.py.
Look at the stills before you call the video done: overlaps, clipped text, empty frames.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
QUALITY_DIRS = {"l": "480p15", "m": "720p30", "h": "1080p60", "p": "1440p60", "k": "2160p60"}


def scene_name(path: Path) -> str:
    m = re.search(r"^class\s+(\w+)\s*\([^)]*Scene[^)]*\)\s*:", path.read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit(f"No Scene subclass found in {path}. Pass the class name as the second argument.")
    return m.group(1)


def save_stills(video: Path, folder: Path, n: int) -> list[Path]:
    import av

    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    out = []
    with av.open(str(video)) as c:
        s = c.streams.video[0]
        dur = float(c.duration / av.time_base) if c.duration else float(s.duration * s.time_base)
        for i in range(n):
            t = dur * (i + 0.5) / n
            c.seek(int(t / s.time_base), stream=s, backward=True)
            for frame in c.decode(s):
                if frame.time is None or frame.time + 1e-3 >= t:
                    p = folder / f"{i + 1:02d}_{t:05.1f}s.png"
                    frame.to_image().save(p)
                    out.append(p)
                    break
    return out


def probe(video: Path) -> tuple[float, bool]:
    import av

    with av.open(str(video)) as c:
        return float(c.duration / av.time_base), bool(c.streams.audio)


def open_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", type=Path)
    ap.add_argument("name", nargs="?", help="Scene class (default: first one in the file)")
    ap.add_argument("--quality", "-q", choices=list(QUALITY_DIRS), default="h")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--stills", type=int, default=6, help="how many evenly spaced frames to save (0 = none)")
    ap.add_argument("--open", action="store_true", help="open the video when done")
    args = ap.parse_args()

    scene = args.scene.resolve()
    work = scene.parent
    name = args.name or scene_name(scene)
    slug = work.name
    out = (args.out or work / (f"{slug}.mp4" if args.quality in "hpk" else f"{slug}-draft.mp4")).resolve()
    audio = work / "audio"
    manifest = audio / "manifest.json"
    if not manifest.exists():
        print("note: no audio/manifest.json, rendering without narration", file=sys.stderr)

    env = dict(os.environ)
    env["EXPLAIN_AUDIO"] = str(audio)
    env["EXPLAIN_SRT"] = str(out.with_suffix(".srt"))
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SCRIPTS), env.get("PYTHONPATH")]))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONWARNINGS", "ignore::SyntaxWarning")  # pydub's old regexes, noise only

    cmd = [sys.executable, "-m", "manim", "render", f"-q{args.quality}", "-v", "WARNING",
           "--progress_bar", "none", "--media_dir", str(work / "media"), str(scene), name]
    print("rendering:", name, f"({QUALITY_DIRS[args.quality]})", flush=True)
    r = subprocess.run(cmd, cwd=work, env=env)
    if r.returncode:
        return r.returncode

    candidates = sorted((work / "media" / "videos" / scene.stem).glob(f"*/{name}.mp4"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise SystemExit("Manim finished but no MP4 was found under media/videos.")
    shutil.copy2(candidates[-1], out)

    duration, has_audio = probe(out)
    print(f"video:     {out}  ({duration:.1f}s, audio: {'yes' if has_audio else 'NO'})")
    srt = out.with_suffix(".srt")
    if srt.exists():
        print(f"subtitles: {srt}")
    if manifest.exists():
        expected = len(json.loads(manifest.read_text(encoding="utf-8"))["segments"])
        said = srt.read_text(encoding="utf-8").count(" --> ") if srt.exists() else 0
        if said < expected:
            print(f"warning:   scene used {said} of {expected} narration segments", file=sys.stderr)
    if args.stills:
        stills = save_stills(out, work / "stills", args.stills)
        print(f"stills:    {len(stills)} frames in {work / 'stills'} (view them before you report)")
    if args.open:
        open_file(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
