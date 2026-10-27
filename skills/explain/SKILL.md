---
name: explain
description: Explain a topic, codebase, paper, concept or model output in the clearest format, following Andrej Karpathy's output ladder - (1) text in ASD-STE100 Simplified Technical English (strict or "80%"), (2) a technical-sheet diagram, (3) an interactive single-file HTML page, (4) a 3Blue1Brown-style narrated explainer video rendered with Manim and voiced by ElevenLabs or free local TTS (Kokoro, Piper). Use when the user runs /explain, asks for an explainer, a breakdown "in STE" or "ASD-STE100", "simplified technical English", a diagram or schematic of how something works, an interactive page or "explain it in HTML", or an explainer video ("3b1b style", "manim", "narrated video"). Also on Russian requests like "объясни через схему", "сделай объяснялку", "объясни на STE", "сделай видео-объяснение". Do NOT use for a quick one-line answer, for editing the user's own prose, or for diagrams that belong inside their codebase (README mermaid, architecture docs).
---

# explain: Karpathy's output ladder

People now spend more time reading what models produce than writing it. Raw prose is the slowest
format to absorb. This skill climbs a ladder of formats. Each rung is easier to absorb than the last:

| Rung | Mode       | Output                                         | Best for                                        |
|------|------------|------------------------------------------------|-------------------------------------------------|
| 1    | `ste`      | Text in ASD-STE100 (strict)                    | Procedures, specs, anything that must be exact  |
| 1    | `ste80`    | Text "80% of the way" to ASD-STE100 (default)  | Normal explanations in chat                     |
| 2    | `diagram`  | Technical-sheet diagram (HTML + inline SVG)    | Structure, flows, comparisons, "how it fits"    |
| 3    | `html`     | Interactive single-file web page               | Things with parameters, steps, or state to play with |
| 4    | `video`    | 3Blue1Brown-style MP4 with narration           | Intuition, math, a story told step by step      |

## 1. Pick the mode

Arguments: `/explain <topic> [ste|ste80|diagram|html|video] [--lang <code>] [--voice <name>] [--engine elevenlabs|kokoro|piper]`

- The user named a mode (or said "схема", "страница", "видео", "STE"): use it.
- No mode given: pick the highest rung that the topic earns, and say which one you picked in one line.
  - A short factual question → `ste80` in chat.
  - A system with parts and connections → `diagram`.
  - A process with knobs, inputs, or stages the reader should try → `html`.
  - An idea that needs intuition built over time (math, algorithms, physics, ML) and the user asked for depth → `video`.
- If you are unsure between two rungs, pick the lower one and offer the next rung in one line at the end.

## 2. Rules for every mode

1. **Keep every fact.** Controlled language changes the form, never the content. Before you finish, compare
   your output with the source and restore any fact, number, caveat, or condition that you dropped.
   Simplified writing has a known failure mode: it quietly loses detail. Check for it every time.
2. **Read the source first.** If the topic is code in this repo, a file, a URL, or a paper, read it before you
   explain it. Do not explain from memory when the source is available.
3. **Words follow STE.** All prose in every mode (diagram labels, page copy, video narration) is written in
   `ste80` unless the user asked for `ste`. Read [references/ste100.md](references/ste100.md) once per session.
4. **Language.** ASD-STE100 is an English standard. If the user writes in another language, answer in that
   language and apply the same principles (short sentences, one idea each, active voice, one term per concept).
5. **Files go to `explainers/<slug>/`** in the current working directory (slug = short kebab-case topic name),
   unless the user named another place. Text in chat needs no file.
6. **Open the result** (`start` on Windows, `open` on macOS, `xdg-open` on Linux) and tell the user the path.
7. **Verify before you hand over.** Look at the output: open the page in a browser tool if you have one, view
   the video stills. Fix overlaps, clipped text, and wrong facts before you report.

## 3. Mode: `ste` and `ste80` (rung 1)

Read [references/ste100.md](references/ste100.md). Then write.

- `ste80` is the default for chat. Short sentences, active voice, one idea per sentence, plain words.
- `ste` is strict. Write the text to a file, then lint it and fix every error:
  ```bash
  python scripts/ste_lint.py draft.md --mode strict
  ```
  (`scripts/` is next to this file. Any Python 3.8+ works; the linter uses only the standard library.)

## 4. Mode: `diagram` (rung 2)

Read [references/diagram.md](references/diagram.md). Copy [assets/sheet-template.html](assets/sheet-template.html)
to `explainers/<slug>/diagram.html` and replace the sample panels. The style is an engineering drawing sheet:
zone border, lettered panels, annotated callouts, title block. For a quick answer in chat a Mermaid block
is fine; say that the full sheet is one command away.

## 5. Mode: `html` (rung 3)

Read [references/html.md](references/html.md). Write one self-contained `explainers/<slug>/index.html`
with real interaction (sliders that drive a live model, step-through, hover definitions). No build step.

## 6. Mode: `video` (rung 4)

Read [references/video.md](references/video.md) before you write anything. Short version:

1. Check the toolchain: `python scripts/doctor.py`. If it reports that video setup is missing (normal on the
   first video after `npx skills add`), tell the user it downloads about 400 MB (Manim, Kokoro voice model),
   then run `python scripts/setup.py`. It installs uv if needed. With no system Python, run
   `uv run --no-project --python 3.12 scripts/setup.py` instead.
2. Write `explainers/<slug>/narration.json` (the script, in segments).
3. Make the voice track: `"$PY" scripts/tts.py explainers/<slug>/narration.json`
   (ElevenLabs if `ELEVENLABS_API_KEY` is set, otherwise free local Kokoro or Piper).
4. Write `explainers/<slug>/scene.py` (Manim, synced to the audio with `narrate.py`).
5. Render and check: `"$PY" scripts/render.py explainers/<slug>/scene.py --quality l` → view the stills → fix → render with `--quality h`.

`$PY` is the video environment's Python. `doctor.py` prints its path.
