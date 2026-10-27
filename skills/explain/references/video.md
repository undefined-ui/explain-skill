# Mode `video`: the 3Blue1Brown-style explainer

Karpathy: "The output format I am most bullish on is fully custom / bespoke explainer videos generated on any
arbitrary topic. ... Create a 3b1b style video explainer on X. Use my ElevenLabs API key for audio narration
(... or find decent free alternatives that use your local compute)."

Pipeline: `narration.json` → `tts.py` (voice, exact durations) → `scene.py` (Manim, synced with `narrate.py`)
→ `render.py` (MP4 + SRT + stills) → you look at the stills → fix → final render.

All commands below run from the skill folder (the folder that holds `SKILL.md`) or with full paths.
`$PY` is the video venv Python that `python scripts/doctor.py` prints:
- Windows: `%USERPROFILE%\.cache\explain-skill\venv\Scripts\python.exe`
- macOS / Linux: `~/.cache/explain-skill/venv/bin/python`

## 0. Toolchain

```bash
python scripts/doctor.py      # exit code 2 = video venv missing or broken
```
If it is missing, tell the user that setup downloads about 400 MB, then run:
```bash
python scripts/setup.py          # installs uv first if needed
```
With no system Python: `uv run --no-project --python 3.12 scripts/setup.py`.

Voice engine, picked by `tts.py --engine auto`:

| Engine       | When                                       | Cost / quality                          |
|--------------|--------------------------------------------|-----------------------------------------|
| `elevenlabs` | `ELEVENLABS_API_KEY` is set                | Paid, best voice, any language          |
| `kokoro`     | No key; lang en, es, fr, it, pt, hi, ja, zh | Free, local CPU, very good English     |
| `piper`      | No key; ru, uk, de, pl (or any `--voice`)  | Free, local CPU, clear but flatter      |

Never print, log, or write the API key into a file. Read it from the environment only.

## 1. Plan the story (before any code)

A 3b1b video is not slides with a voice. It is one visual idea that transforms on screen while the
narration explains why. Write a short plan for yourself:

1. **The question.** One sentence the viewer wants answered. Open with it.
2. **The one picture.** The single visual that holds the answer (a bar chart that reshapes, a vector that
   rotates, a grid that warps, a tree that grows). Most of the video transforms this picture.
3. **Concrete before abstract.** Start with a specific example with real numbers. Generalize after.
4. **Beats.** 4-10 segments, each 1-3 sentences and one visual change. Typical arc:
   hook → concrete example → the mechanism, step by step → the surprising consequence → recap.
5. **Length.** 45-120 seconds unless the user asks for more. About 150 spoken words per minute.

## 2. Write `narration.json`

```json
{
  "title": "Softmax temperature",
  "lang": "en",
  "voice": {"kokoro": "am_michael", "elevenlabs": "JBFqnCBsd6RMkjVDRZzb"},
  "segments": [
    {"id": "hook", "text": "A language model does not pick the next word directly.", "pause": 0.4},
    {"id": "scores", "text": "It gives every word a score. Then it rolls weighted dice."}
  ]
}
```

- Narration is **STE-80**: short sentences, active voice, one idea per sentence, one term per concept.
  This is also what sounds best from a TTS engine.
- Write numbers and symbols the way they are spoken: "two point five", "T equals zero point three",
  "x squared". TTS engines read "2.5x" and "e^x" badly.
- `pause` is silence after the clip in seconds (default 0.3). Use 0.5-1.0 before a new idea.
- `voice` can be a string or a per-engine map. Good picks: Kokoro `af_heart` (default), `am_michael`,
  `bm_george`; Piper `ru_RU-dmitri-medium` (default ru), `ru_RU-irina-medium`.
- `lang` is the narration language. For Russian use `"lang": "ru"` (Piper, or ElevenLabs if a key is set).

Then make the audio:
```bash
"$PY" scripts/tts.py explainers/<slug>/narration.json
```
It prints the duration and words per minute of each clip. Edit a line and run it again: unchanged clips are cached.

## 3. Write `scene.py`

Start from `assets/video/example/scene.py`. Rules:

**Sync.** Wrap each beat in `with say("<id>") as seg:`. Leaving the block waits for the clip to end.
Keep the animations inside a block shorter than `seg.duration`. Use `seg.left()` to fill the rest of a clip.

```python
from manim import *
from narrate import Narration

class Explainer(Scene):
    def construct(self):
        self.camera.background_color = "#0f1115"
        say = Narration(self)
        with say("hook") as seg:
            self.play(Write(title), run_time=1.5)
            self.play(Create(graph), run_time=seg.left())
```

**3b1b visual language.**
- Dark background (`#0f1115`), white text, one accent family: `BLUE` for the main object, `YELLOW` for
  "watch this", `RED`/`GREEN` only for bad/good. Same concept = same color for the whole video.
- **Transform, do not cut.** Use `ReplacementTransform`, `TransformMatchingShapes`, `ValueTracker` +
  `always_redraw`, `.animate`. The viewer should see where every new thing comes from.
- **The math is real.** Compute positions with numpy from the real formula. Do not fake a curve.
- **Little text on screen.** The voice carries the words. On screen: a title, labels, at most one formula.
- **Guide the eye.** `Indicate`, `Circumscribe`, `Flash`, or a color change on the thing the narration names,
  at the moment it names it.
- **Breathing room.** One idea on screen at a time. Clear the old picture (`FadeOut`) before a new topic.
- **Motion speed.** 0.6-2 s per animation. `LaggedStart` for groups. No spin or bounce effects.
- No characters or mascots from other creators (no "pi creatures"). Make the style, not a copy.

**Layout.** The frame is 14.2 × 8 units, centered at the origin (x: -7.1..7.1, y: -4..4).
- Keep content inside x ±6.5 and y ±3.6. Title at `to_edge(UP, buff=0.45)`.
- Position with `.next_to()`, `.arrange()`, `.to_edge()`, `VGroup`, never by eye-balled numbers only.
- Text: `font_size` 24-48. A 40-character line at size 40 is about 10 units wide.

**No LaTeX by default.** `MathTex`, `Tex`, `DecimalNumber`, `Integer`, and number labels on `NumberLine`/`Axes`
need a LaTeX install. If `doctor.py` says "LaTeX: no", use `Text`, `MarkupText` (`e<sup>x</sup>`, `x<sub>i</sub>`),
and `always_redraw(lambda: Text(f"{v:.2f}"))` for live numbers. Place axis labels yourself.

## 4. Render, look, fix

```bash
"$PY" scripts/render.py explainers/<slug>/scene.py --quality l      # draft: 480p15, fast
```
It writes `<slug>-draft.mp4`, `<slug>-draft.srt`, and 6 stills in `stills/`. **Open every still** (Read the PNG).
Check:
- [ ] No text overlaps another object or leaves the frame.
- [ ] Every frame has something to look at (no empty black frames).
- [ ] The highlighted object matches what the narration says at that moment.
- [ ] `audio: yes` in the render output, and no "used N of M segments" warning.

Fix, render the draft again, then make the final:
```bash
"$PY" scripts/render.py explainers/<slug>/scene.py --quality h --open    # 1080p60
```

Report to the user: the MP4 path, its length, the voice engine used, and the SRT path (it is ready to upload as captions).

## Errors you will meet

| Symptom                                   | Fix                                                                 |
|-------------------------------------------|---------------------------------------------------------------------|
| `FileNotFoundError: latex`                | You used MathTex/Tex/DecimalNumber. Switch to Text/MarkupText.      |
| `manifest.json not found`                 | Run `tts.py` first, or the scene is not in the folder with `audio/`. |
| `No module named narrate`                 | Run through `render.py`, not `manim` directly (it sets PYTHONPATH). |
| Voice starts late, gaps between clips      | Animations in a block are longer than the clip. Shorten run_time.   |
| Old shapes stay on screen behind new ones ("ghosts") | `ReplacementTransform(a, group[0])` adds `group[0]` itself to the scene. Remove the parts (`self.remove(group[0], group[1])`), not the group. |
| Labels touch the frame edge               | Keep content inside x ±6.5. Measure: `mob.get_left()[0]`, `mob.width`. |
| ElevenLabs HTTP 401 / 402 / 429           | Key wrong, quota out, or rate limit. Re-run with `--engine kokoro`. |
| Linux: `pycairo` / `manimpango` build fails | Install `libcairo2-dev libpango1.0-dev pkg-config python3-dev`.    |
