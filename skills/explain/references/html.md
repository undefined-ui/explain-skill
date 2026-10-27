# Mode `html`: the interactive explainer page

Karpathy: "Ask for output 'in HTML' to get a beautiful, interactive webpage. LLMs are getting really good
at frontend and can create beautiful experiences, animations, etc."

The output is one self-contained `explainers/<slug>/index.html`. No build step, no server, no framework
that needs a compiler. It opens with a double-click.

## What makes it worth more than a diagram

A page earns rung 3 only if the reader can **do** something that changes what they see. Pick at least one:

| Interaction          | Use it for                                              | Example                                      |
|----------------------|---------------------------------------------------------|----------------------------------------------|
| Slider → live model  | A quantity that depends on another                      | Temperature slider reshapes a softmax bar chart |
| Step-through         | A process in stages                                     | "Next" walks a packet through a TCP handshake |
| Play with input      | A transform the reader can test                          | Type text, see the tokens and their ids       |
| Hover / tap reveal   | Dense figures with many parts                            | Hover a layer to see its shape and role       |
| Toggle compare       | Two designs, before/after                                | Toggle between O(n²) and O(n log n) on a timeline |
| Scroll story         | A narrative where each section changes one figure        | Sticky figure, text steps scroll past         |

Run the real algorithm in JavaScript when you can (a real softmax, a real tokenizer on a toy vocabulary,
a real sort). A fake animation that only looks right teaches the wrong thing.

## Page structure

1. **Hook** (one screen): the question the page answers, in one sentence, and the figure that answers it.
2. **The interactive core**: the main toy, big, with 1-3 controls and a live readout.
3. **Step by step**: 3-6 short sections. Each section changes one thing in a figure.
4. **Try this**: 2-3 concrete things to do with the controls, each with what the reader should notice.
5. **Summary**: 3-5 bullets in STE-80. Then the source (file, paper, link).

## Build rules

- **Single file.** Inline CSS and JS. Allowed external loads: Google Fonts, and pinned CDN versions
  of a library when it saves real work (`https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm`,
  `https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js`). Pin exact versions.
- **Tokens on `:root`.** Define colors as CSS variables. Support dark mode with
  `@media (prefers-color-scheme: dark)`. Give `body` an explicit background.
- **Typography.** One sans for text, one mono for code and numbers. Body 16-18 px, line length 60-75 characters.
- **Phones.** Works at 375 px wide: 16 px side padding, no horizontal scroll, touch targets ≥ 40 px.
- **Motion.** Animate state changes (200-400 ms ease), not decoration. Respect `prefers-reduced-motion`.
- **Copy is STE-80.** Short sentences, active voice, one term per concept. Label every axis and unit.
- **Accessible.** Real `<button>` and `<input type="range">` with `<label>`. Visible focus. Figures get `aria-label`.
- **No dead ends.** Every control has a visible effect within one frame.

## Skeleton

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Softmax Temperature</title>
<style>
  :root { --bg:#fbfaf7; --ink:#1b1b1b; --muted:#6b6b6b; --accent:#1f5aa6; --accent-fill:#dde8f6; --line:#d9d6cf;
          --sans: system-ui, sans-serif; --mono: ui-monospace, monospace; }
  @media (prefers-color-scheme: dark) { :root { --bg:#141619; --ink:#e8e6e1; --muted:#9a9890; --accent:#7fb0ec; --accent-fill:#1d2c40; --line:#33363b; } }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink); font:17px/1.55 var(--sans); }
  main { max-width: 980px; margin: 0 auto; padding: 32px 16px 80px; }
  @media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
</head>
<body>
<main>
  <h1>How temperature changes a model's choices</h1>
  <!-- core toy: controls + live figure + readout -->
</main>
<script>
  // state → render(state). Every control writes state, then calls render().
</script>
</body>
</html>
```

## Verify

Open the page. If a browser tool is available, load the file, click every control, and take one screenshot
at desktop width and one at 375 px. Check the console for errors. Fix before you report.
