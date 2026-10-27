"""Example: a 3b1b-style explainer synced to narration.json.

    "$PY" scripts/tts.py assets/video/example/narration.json
    "$PY" scripts/render.py assets/video/example/scene.py --quality l

Patterns to copy: one Narration block per segment, real math driving the visuals
(numpy softmax, a ValueTracker for temperature), always_redraw for live updates,
Text/MarkupText instead of LaTeX, one accent color for "the thing to watch".
"""

import numpy as np
from manim import (
    BLUE, DOWN, GREY_A, GREY_B, GREY_D, LEFT, RED, RIGHT, UP, WHITE, YELLOW,
    Create, Dot, FadeIn, FadeOut, GrowFromEdge, Indicate, LaggedStart, Line, MarkupText,
    Rectangle, ReplacementTransform, Scene, Text, ValueTracker, VGroup, Write, always_redraw,
)
from narrate import Narration

BG = "#0f1115"
WORDS = ["cat", "dog", "car", "sky", "tea"]
SCORES = np.array([3.0, 2.2, 1.5, 0.8, 0.3])
BASE_Y, MAX_H = -2.3, 4.0
X0, DX, BAR_W = -4.4, 2.2, 1.1
T_MIN, T_MAX = 0.2, 3.0


def softmax(z, t):
    e = np.exp((z - z.max()) / t)
    return e / e.sum()


def bars(heights, colors):
    return VGroup(*[
        Rectangle(width=BAR_W, height=max(h, 0.03), fill_color=c, fill_opacity=0.9, stroke_width=0)
        .move_to([X0 + i * DX, BASE_Y + max(h, 0.03) / 2, 0])
        for i, (h, c) in enumerate(zip(heights, colors))
    ])


def values(bar_group, texts):
    return VGroup(*[Text(t, font_size=24, color=GREY_A).next_to(b, UP, buff=0.12) for b, t in zip(bar_group, texts)])


def prob_chart(t):
    p = softmax(SCORES, t)
    colors = [YELLOW if i == 0 else BLUE for i in range(len(p))]
    b = bars(p * MAX_H, colors)
    return VGroup(b, values(b, [f"{v:.0%}" for v in p]))


class Explainer(Scene):
    def construct(self):
        self.camera.background_color = BG
        say = Narration(self)

        title = Text("How temperature shapes a model's choice", font_size=40).to_edge(UP, buff=0.45)
        axis = Line([X0 - 1, BASE_Y, 0], [X0 + 4 * DX + 1, BASE_Y, 0], color=GREY_B, stroke_width=2)
        labels = VGroup(*[Text(w, font_size=30).move_to([X0 + i * DX, BASE_Y - 0.42, 0]) for i, w in enumerate(WORDS)])

        score_bars = bars(SCORES / SCORES.max() * MAX_H * 0.75, [GREY_D] * len(SCORES))
        score_vals = values(score_bars, [f"{s:.1f}" for s in SCORES])
        tag = Text("score", font_size=24, color=GREY_B).move_to([5.6, 1.6, 0])

        with say("hook"):
            self.play(Write(title), run_time=1.4)
            self.play(Create(axis), FadeIn(labels, shift=UP * 0.2), run_time=1.0)
            self.play(LaggedStart(*[GrowFromEdge(b, DOWN) for b in score_bars], lag_ratio=0.15),
                      FadeIn(score_vals), FadeIn(tag), run_time=1.8)
            self.play(Indicate(score_bars[0], color=WHITE), run_time=1.0)

        formula = MarkupText("p = e<sup>score / T</sup>  ÷  sum of all e<sup>score / T</sup>", font_size=30)
        formula.next_to(title, DOWN, buff=0.4)
        start = prob_chart(1.0)
        tag2 = Text("probability", font_size=24, color=GREY_B).move_to(tag)
        total = Text("sum = 100%", font_size=24, color=GREY_A).next_to(tag2, DOWN, buff=0.25)

        with say("softmax"):
            self.play(FadeIn(formula, shift=DOWN * 0.2), run_time=1.0)
            self.play(ReplacementTransform(score_bars, start[0]), ReplacementTransform(score_vals, start[1]),
                      ReplacementTransform(tag, tag2), run_time=2.0)
            self.play(FadeIn(total), run_time=0.6)

        # Hand over from the static chart to a live one. ReplacementTransform added start[0] and
        # start[1] to the scene as separate mobjects, so remove those, not the `start` group.
        temp = ValueTracker(1.0)
        chart = always_redraw(lambda: prob_chart(temp.get_value()))
        self.remove(start[0], start[1])
        self.add(chart)

        track = Line([-2.2, -3.55, 0], [2.2, -3.55, 0], color=GREY_D, stroke_width=6)
        knob = always_redraw(lambda: Dot(
            track.point_from_proportion((temp.get_value() - T_MIN) / (T_MAX - T_MIN)), radius=0.12, color=WHITE))
        t_text = always_redraw(lambda: Text(f"T = {temp.get_value():.1f}", font_size=28).next_to(track, RIGHT, buff=0.45))
        cold = Text("cold", font_size=22, color=BLUE).next_to(track, LEFT, buff=0.3)
        hot = Text("hot", font_size=22, color=RED).move_to(cold).set_x(t_text.get_right()[0] + 0.7)

        with say("cold"):
            self.play(FadeIn(VGroup(track, knob, t_text, cold, hot)), run_time=0.8)
            self.play(temp.animate.set_value(0.3), run_time=3.0)

        with say("hot"):
            self.play(temp.animate.set_value(2.6), run_time=3.5)

        recap = VGroup(
            Text("Low T  →  focused, repeatable", font_size=40, color=BLUE),
            Text("High T  →  varied, surprising", font_size=40, color=RED),
        ).arrange(DOWN, buff=0.6)

        with say("recap"):
            self.play(FadeOut(VGroup(chart, axis, labels, tag2, total, formula, track, knob, t_text, cold, hot)),
                      run_time=0.8)
            self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in recap], lag_ratio=0.5), run_time=1.6)
