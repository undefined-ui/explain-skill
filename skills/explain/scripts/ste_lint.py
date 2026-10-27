#!/usr/bin/env python3
"""Lint text against ASD-STE100 writing rules (strict) or the softer "80%" profile.

    python ste_lint.py draft.md                 # 80% profile, warnings only
    python ste_lint.py draft.md --mode strict   # strict STE, exit code 1 on errors
    cat draft.md | python ste_lint.py -         # read stdin
    python ste_lint.py draft.md --allow "landing gear,bearing"

The checks are mechanical heuristics. They catch long sentences, long paragraphs,
-ing forms, perfect tenses, likely passives, semicolons, contractions, filler,
and words with a plain substitute. They cannot judge meaning: a clean lint run
does not prove that the text is good STE. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass

PROCEDURAL_LIMIT = 20
DESCRIPTIVE_LIMIT = 25
PARAGRAPH_LIMIT = 6

# word -> suggestion. Single words also match their -s/-ed/-ing forms.
SUBSTITUTIONS = {
    "commence": "start",
    "ensure": "make sure",
    "prior to": "before",
    "replenish": "fill",
    "utilize": "use",
    "utilise": "use",
    "approximately": "about",
    "in order to": "to",
    "accomplish": "do, complete",
    "additional": "more",
    "adjacent to": "near, next to",
    "assist": "help",
    "attempt": "try",
    "capability": "can (verb)",
    "comprise": "contain, consist of",
    "demonstrate": "show",
    "due to the fact that": "because",
    "endeavor": "try",
    "facilitate": "help, make easy",
    "implement": "do, make, install",
    "indicate": "show",
    "initiate": "start",
    "leverage": "use",
    "numerous": "many",
    "obtain": "get",
    "perform": "do",
    "proceed": "go, continue",
    "provide": "give",
    "purchase": "buy",
    "require": "need",
    "sufficient": "enough",
    "terminate": "stop",
    "subsequently": "then, after this",
    "therefore": "thus, as a result",
    "verify": "make sure, check",
    "whether or not": "if",
    "set up": "install, prepare",
    "carry out": "do",
    "find out": "find, identify",
    "make use of": "use",
    "etc": "give the full list, or write 'for example'",
}

FILLER = [
    "it is worth noting", "it's worth noting", "it is important to note", "it's important to note",
    "needless to say", "basically", "essentially", "actually", "very", "really", "quite",
    "various", "significantly", "in terms of", "at the end of the day", "the fact that",
    "a number of", "it should be noted", "delve", "seamless", "robust",
]

# -ing words that are not verb forms (or are so common as nouns that flagging them is noise).
ING_NOT_VERBS = {
    "thing", "things", "nothing", "something", "anything", "everything", "string", "strings",
    "ring", "rings", "spring", "springs", "king", "wing", "wings", "swing", "bring", "brings",
    "sing", "sting", "during", "morning", "evening", "ceiling", "bearing", "bearings",
    "building", "buildings", "ping", "bring", "fitting", "fittings", "wiring", "housing",
    "coupling", "tubing", "lining", "setting", "settings", "warning", "warnings", "opening",
    "openings", "landing", "padding", "spacing", "rating", "ratings", "drawing", "drawings",
    "meaning", "meanings", "beginning",
}

IRREGULAR_PARTICIPLES = (
    "been|done|gone|made|seen|taken|given|written|shown|known|run|begun|become|found|got|gotten|"
    "put|set|built|sent|left|kept|held|brought|thought|told|read|cut|hit|lost|paid|said|sold|"
    "spent|stood|understood|won|worn|broken|chosen|driven|fallen|forgotten|frozen|hidden|ridden|"
    "risen|spoken|stolen|thrown|woken"
)
PERFECT_RE = re.compile(rf"\b(has|have|had)\s+(not\s+)?(\w+ed|{IRREGULAR_PARTICIPLES})\b", re.I)
PASSIVE_RE = re.compile(
    rf"\b(is|are|was|were|be|been|being)\s+(not\s+)?(\w+ed|{IRREGULAR_PARTICIPLES})\b(\s+by\b)?", re.I
)
CONTRACTION_RE = re.compile(
    r"\b\w+(n't|'re|'ve|'ll|'d|'m)\b|\b(it's|that's|there's|what's|here's|let's|who's)\b", re.I
)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’\-/.·]*")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])[\"')\]]*\s+(?=[\"'(\[]?[A-Z0-9])")
LIST_ITEM_RE = re.compile(r"^\s*(\d+[.)]|[-*+])\s+")
NUMBERED_ITEM_RE = re.compile(r"^\s*\d+[.)]\s+")


@dataclass
class Issue:
    line: int
    level: str  # "error" | "warn"
    rule: str
    message: str
    excerpt: str


def substitution_patterns() -> list[tuple[re.Pattern, str, str]]:
    out = []
    for word, suggestion in SUBSTITUTIONS.items():
        if " " in word:
            pattern = r"\b" + r"\s+".join(map(re.escape, word.split())) + r"\b"
        else:
            if word.endswith("y"):
                pattern = rf"\b(?:{re.escape(word)}|{re.escape(word[:-1])}(?:ies|ied)|{re.escape(word)}ing)\b"
            else:
                stem = word[:-1] if word.endswith("e") else word
                pattern = rf"\b(?:{re.escape(word)}|{re.escape(stem)}(?:s|es|ed|d|ing))\b"
            if word == "etc":
                pattern = r"\betc\b\.?"
        out.append((re.compile(pattern, re.I), word, suggestion))
    return out


def blocks(text: str):
    """Yield (first_line_number, kind, text) for paragraphs and list items. Skips code and tables."""
    in_code = False
    buf: list[str] = []
    start = 0
    kind = "para"

    def flush():
        nonlocal buf
        if buf:
            yield_value = (start, kind, " ".join(s.strip() for s in buf))
            buf = []
            return yield_value
        return None

    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.lstrip().startswith(("```", "~~~")):
            in_code = not in_code
            item = flush()
            if item:
                yield item
            continue
        if in_code or line.lstrip().startswith(("|", ">", "<")) or re.match(r"^\s*#{1,6}\s", line):
            item = flush()
            if item:
                yield item
            continue
        if not line.strip():
            item = flush()
            if item:
                yield item
            continue
        if LIST_ITEM_RE.match(line):
            item = flush()
            if item:
                yield item
            start, kind = i, ("step" if NUMBERED_ITEM_RE.match(line) else "item")
            buf = [LIST_ITEM_RE.sub("", line)]
            continue
        if not buf:
            start, kind = i, "para"
        buf.append(line)
    item = flush()
    if item:
        yield item


def strip_markup(s: str) -> str:
    s = re.sub(r"`[^`]*`", "X", s)  # inline code counts as one word
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # links
    s = re.sub(r"[*_]{1,3}", "", s)
    return s


def lint(text: str, mode: str, allow: set[str]) -> list[Issue]:
    strict = mode == "strict"
    sev = "error" if strict else "warn"
    issues: list[Issue] = []
    subs = substitution_patterns()
    filler = [(re.compile(r"\b" + re.escape(f) + r"\b", re.I), f) for f in FILLER]

    for line_no, kind, raw in blocks(text):
        body = strip_markup(raw)
        sentences = [s for s in SENTENCE_SPLIT_RE.split(body) if WORD_RE.search(s)]
        if kind == "para" and len(sentences) > PARAGRAPH_LIMIT:
            issues.append(Issue(line_no, sev, "paragraph-length",
                                f"{len(sentences)} sentences (max {PARAGRAPH_LIMIT}). Split by topic.",
                                body[:70]))
        limit = PROCEDURAL_LIMIT if kind == "step" else DESCRIPTIVE_LIMIT
        for s in sentences:
            n = len(WORD_RE.findall(s))
            if n > limit:
                issues.append(Issue(line_no, sev, "sentence-length",
                                    f"{n} words (max {limit} for {'procedural' if kind == 'step' else 'descriptive'}).",
                                    s[:70]))

        lowered = body.lower()
        for rx, word, suggestion in subs:
            for m in rx.finditer(body):
                if any(a in lowered[max(0, m.start() - 30): m.end() + 30] for a in allow):
                    continue
                issues.append(Issue(line_no, sev, "word", f'"{m.group(0)}" -> {suggestion}', ""))
        if ";" in body:
            issues.append(Issue(line_no, sev, "semicolon", "Do not use semicolons. Make two sentences.", ""))
        for m in CONTRACTION_RE.finditer(body):
            issues.append(Issue(line_no, sev, "contraction", f'"{m.group(0)}": write the full form.', ""))
        for rx, f in filler:
            if rx.search(body):
                issues.append(Issue(line_no, "warn", "filler", f'"{f}" adds no meaning. Delete it or be specific.', ""))

        if not strict:
            continue
        for w in WORD_RE.findall(body):
            lw = w.lower().strip(".'’")
            if lw.endswith("ing") and len(lw) > 4 and lw not in ING_NOT_VERBS and not any(lw in a for a in allow):
                issues.append(Issue(line_no, "error", "ing-form",
                                    f'"{w}": -ing form. Use simple present, a noun, or add it to --allow if it is a technical name.',
                                    ""))
        for m in PERFECT_RE.finditer(body):
            issues.append(Issue(line_no, "error", "perfect-tense",
                                f'"{m.group(0)}": perfect tense. Use simple past or present.', ""))
        for m in PASSIVE_RE.finditer(body):
            level = "error" if kind == "step" else "warn"
            issues.append(Issue(line_no, level, "passive",
                                f'"{m.group(0)}": likely passive. Use the active voice'
                                + (" (passive is not allowed in procedures)." if kind == "step"
                                   else " unless the actor is unknown. A participle used as an adjective is OK."),
                                ""))
    return issues


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", help="file to lint, or - for stdin")
    ap.add_argument("--mode", choices=["strict", "80"], default="80")
    ap.add_argument("--allow", default="", help="comma-separated technical names to skip (for -ing and word checks)")
    args = ap.parse_args(argv)

    if args.path == "-":
        text = sys.stdin.read()
    else:
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
    allow = {a.strip().lower() for a in args.allow.split(",") if a.strip()}
    issues = lint(text, args.mode, allow)

    for it in sorted(issues, key=lambda x: (x.line, x.level != "error")):
        tail = f"  | {it.excerpt}..." if it.excerpt else ""
        print(f"line {it.line:>4}  {it.level:<5}  {it.rule:<16} {it.message}{tail}")
    errors = sum(1 for i in issues if i.level == "error")
    warns = len(issues) - errors
    print(f"\n{errors} error(s), {warns} warning(s) [mode: {args.mode}]")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
