"""Sync Manim animations to the narration made by tts.py.

    from manim import *
    from narrate import Narration

    class Explainer(Scene):
        def construct(self):
            say = Narration(self)
            with say("hook") as seg:                        # the clip starts here
                self.play(Write(title), run_time=seg.duration * 0.5)
                self.play(FadeIn(dice))
            # leaving the block waits until the clip and its pause are over
            with say("logits") as seg:
                self.play(Create(bars), run_time=seg.left())  # fill the rest of the clip

`seg.duration` is the clip length in seconds, `seg.left()` is the time still left in it.
If your animations run longer than the clip, the next clip starts late (a gap, not an overlap).

render.py sets EXPLAIN_AUDIO to the audio folder. Without it, audio/ next to the current
directory is used. It also writes subtitles.srt from the real start time of every clip.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Segment:
    id: str
    text: str
    path: Path
    duration: float
    pause: float
    _scene: object = field(repr=False, default=None)
    _start: float = 0.0

    def left(self, minimum: float = 0.1) -> float:
        """Seconds left in this clip (never below `minimum`, so it is safe as a run_time)."""
        return max(minimum, self._start + self.duration - _now(self._scene))


def _now(scene) -> float:
    return float(scene.renderer.time)


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


class Narration:
    def __init__(self, scene, audio_dir: str | os.PathLike | None = None):
        self.scene = scene
        self.dir = Path(audio_dir or os.environ.get("EXPLAIN_AUDIO") or Path.cwd() / "audio")
        manifest = self.dir / "manifest.json"
        if not manifest.exists():
            raise FileNotFoundError(f"{manifest} not found. Run tts.py on narration.json first.")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.order = [s["id"] for s in data["segments"]]
        self.segments = {
            s["id"]: Segment(s["id"], s["text"], self.dir / s["file"], s["duration"], s.get("pause", 0.3))
            for s in data["segments"]
        }
        self.used: list[tuple[float, float, str]] = []
        self.srt = Path(os.environ.get("EXPLAIN_SRT") or self.dir / "subtitles.srt")

    def __getitem__(self, seg_id: str) -> Segment:
        return self.segments[seg_id]

    @property
    def total(self) -> float:
        return sum(s.duration + s.pause for s in self.segments.values())

    @contextmanager
    def __call__(self, seg_id: str):
        if seg_id not in self.segments:
            raise KeyError(f"No segment {seg_id!r} in manifest. Known: {', '.join(self.order)}")
        seg = self.segments[seg_id]
        seg._scene, seg._start = self.scene, _now(self.scene)
        self.scene.add_sound(str(seg.path))
        yield seg
        end = seg._start + seg.duration + seg.pause
        remaining = end - _now(self.scene)
        if remaining > 0.01:
            self.scene.wait(remaining)
        self.used.append((seg._start, seg._start + seg.duration, seg.text))
        self._write_srt()

    def unused(self) -> list[str]:
        said = {t for _, _, t in self.used}
        return [i for i in self.order if self.segments[i].text not in said]

    def _write_srt(self) -> None:
        lines = []
        for n, (a, b, text) in enumerate(self.used, 1):
            lines += [str(n), f"{_srt_time(a)} --> {_srt_time(b)}", text, ""]
        try:
            self.srt.write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            pass
