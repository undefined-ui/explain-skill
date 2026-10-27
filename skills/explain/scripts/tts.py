#!/usr/bin/env python3
"""Turn narration.json into one WAV per segment plus audio/manifest.json with exact durations.

    "$PY" tts.py explainers/<slug>/narration.json
    "$PY" tts.py narration.json --engine kokoro --voice am_michael --speed 1.05
    "$PY" tts.py narration.json --engine piper --lang ru

narration.json:
    {
      "title": "Why softmax has a temperature",
      "lang": "en",                      # optional, default en
      "voice": "af_heart",               # optional, engine-specific
      "speed": 1.0,                      # optional
      "segments": [
        {"id": "hook", "text": "Every time a model picks a word, it rolls weighted dice.", "pause": 0.4},
        {"id": "logits", "text": "First, the model gives each word a score."}
      ]
    }

Engines (--engine auto picks the first that fits):
    elevenlabs  ELEVENLABS_API_KEY is set. Optional ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL.
    kokoro      Free, local. en, es, fr, it, pt, hi, ja, zh.
    piper       Free, local. ru, uk, de, pl by default, or any Piper voice name via --voice.

Unchanged segments are reused, so you can edit one line and run this again cheaply.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import KOKORO_DIR, PIPER_BASE, PIPER_DIR, kokoro_ready  # noqa: E402

# lang -> (kokoro lang code, default voice)
KOKORO_LANGS = {
    "en": ("en-us", "af_heart"), "en-us": ("en-us", "af_heart"), "en-gb": ("en-gb", "bf_emma"),
    "es": ("es", "ef_dora"), "fr": ("fr-fr", "ff_siwis"), "it": ("it", "if_sara"),
    "pt": ("pt-br", "pf_dora"), "hi": ("hi", "hf_alpha"), "ja": ("ja", "jf_alpha"), "zh": ("cmn", "zf_xiaobei"),
}
PIPER_DEFAULTS = {
    "ru": "ru_RU-dmitri-medium", "uk": "uk_UA-ukrainian_tts-medium",
    "de": "de_DE-thorsten-medium", "pl": "pl_PL-darkman-medium", "en": "en_US-lessac-medium",
}
ELEVEN_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # "George", a stock ElevenLabs voice
ELEVEN_MODEL = "eleven_multilingual_v2"
SAMPLE_RATE = 24000


def pick_engine(requested: str, lang: str) -> str:
    if requested != "auto":
        return requested
    if os.environ.get("ELEVENLABS_API_KEY"):
        return "elevenlabs"
    if lang in KOKORO_LANGS and kokoro_ready():
        return "kokoro"
    return "piper"


# ── engines: each returns (int16 numpy array, sample_rate) ──────────────────

def eleven(text: str, voice: str, speed: float, prev: str, nxt: str):
    import numpy as np

    key = os.environ["ELEVENLABS_API_KEY"]
    model = os.environ.get("ELEVENLABS_MODEL", ELEVEN_MODEL)
    body = {"text": text, "model_id": model, "previous_text": prev, "next_text": nxt}
    if speed != 1.0:
        body["voice_settings"] = {"speed": max(0.7, min(1.2, speed))}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_{SAMPLE_RATE}",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            pcm = r.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        raise RuntimeError(f"ElevenLabs HTTP {e.code}: {detail}") from None
    return np.frombuffer(pcm, dtype="<i2"), SAMPLE_RATE


_kokoro = None


def kokoro(text: str, voice: str, speed: float, lang: str):
    import numpy as np
    from kokoro_onnx import Kokoro

    global _kokoro
    if _kokoro is None:
        _kokoro = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.int8.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
    code = KOKORO_LANGS.get(lang, ("en-us", ""))[0]
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=code)
    return (np.clip(samples, -1, 1) * 32767).astype("<i2"), sr


def piper_model(name: str) -> Path:
    """Download a Piper voice like ru_RU-dmitri-medium from Hugging Face on first use."""
    model = PIPER_DIR / f"{name}.onnx"
    if model.exists() and model.with_suffix(".onnx.json").exists():
        return model
    parts = name.split("-")
    if len(parts) < 3:
        raise SystemExit(f"Piper voice names look like ru_RU-dmitri-medium, got {name!r}")
    locale, speaker, quality = parts[0], "-".join(parts[1:-1]), parts[-1]
    base = f"{PIPER_BASE}/{locale.split('_')[0]}/{locale}/{speaker}/{quality}/{name}"
    PIPER_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in (".onnx", ".onnx.json"):
        dest = PIPER_DIR / f"{name}{suffix}"
        print(f"    downloading Piper voice {dest.name}", flush=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        urllib.request.urlretrieve(base + suffix, tmp)
        tmp.replace(dest)
    return model


_piper = {}


def piper(text: str, voice: str, speed: float):
    import io

    import numpy as np
    from piper import PiperVoice

    if voice not in _piper:
        _piper[voice] = PiperVoice.load(str(piper_model(voice)))
    pv = _piper[voice]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        try:
            from piper import SynthesisConfig
            pv.synthesize_wav(text, wf, syn_config=SynthesisConfig(length_scale=1.0 / speed))
        except ImportError:
            pv.synthesize_wav(text, wf)
    buf.seek(0)
    with wave.open(buf, "rb") as wf:
        sr = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2")
    return data, sr


# ── main ───────────────────────────────────────────────────────────────────

def default_voice(engine: str, lang: str) -> str:
    if engine == "elevenlabs":
        return os.environ.get("ELEVENLABS_VOICE_ID", ELEVEN_VOICE)
    if engine == "kokoro":
        return KOKORO_LANGS.get(lang, KOKORO_LANGS["en"])[1]
    if lang not in PIPER_DEFAULTS:
        raise SystemExit(f"No default Piper voice for lang={lang!r}. Pass --voice <name> "
                         "(list: https://huggingface.co/rhasspy/piper-voices).")
    return PIPER_DEFAULTS[lang]


def voice_fits(engine: str, voice: str) -> bool:
    """A voice name from narration.json may belong to another engine (af_heart is Kokoro only)."""
    if engine == "kokoro":
        return re.fullmatch(r"[a-z]{2}_[a-z]+", voice) is not None
    if engine == "piper":
        return re.fullmatch(r"[a-z]{2,3}_[A-Z]{2}-.+-(x_low|low|medium|high)", voice) is not None
    return re.fullmatch(r"[A-Za-z0-9]{16,32}", voice) is not None


def write_wav(path: Path, data, sr: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.astype("<i2").tobytes())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("narration", type=Path)
    ap.add_argument("--engine", choices=["auto", "elevenlabs", "kokoro", "piper"], default="auto")
    ap.add_argument("--voice")
    ap.add_argument("--lang")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--out", type=Path, help="output dir (default: audio/ next to narration.json)")
    args = ap.parse_args()

    spec = json.loads(args.narration.read_text(encoding="utf-8"))
    segments = spec["segments"]
    ids = [s["id"] for s in segments]
    if len(ids) != len(set(ids)):
        raise SystemExit("Segment ids must be unique.")
    lang = (args.lang or spec.get("lang") or "en").lower()
    speed = args.speed or spec.get("speed") or 1.0
    engine = pick_engine(args.engine, lang)
    wanted = args.voice or spec.get("voice")
    if isinstance(wanted, dict):  # {"kokoro": "am_michael", "elevenlabs": "<voice id>"}
        wanted = wanted.get(engine)
    voice = wanted if wanted and voice_fits(engine, wanted) else default_voice(engine, lang)

    out = args.out or args.narration.parent / "audio"
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    old = {}
    if manifest_path.exists():
        old = {s["id"]: s for s in json.loads(manifest_path.read_text(encoding="utf-8"))["segments"]}

    print(f"engine={engine} voice={voice} lang={lang} speed={speed} segments={len(segments)}", flush=True)
    rows, total = [], 0.0
    for i, seg in enumerate(segments):
        text = seg["text"].strip()
        h = hashlib.sha1(json.dumps([engine, voice, lang, speed, text]).encode()).hexdigest()[:16]
        wav = out / f"{seg['id']}.wav"
        prev = old.get(seg["id"])
        if prev and prev.get("hash") == h and wav.exists():
            duration = prev["duration"]
            status = "cached"
        else:
            if engine == "elevenlabs":
                prev_text = segments[i - 1]["text"] if i else ""
                next_text = segments[i + 1]["text"] if i + 1 < len(segments) else ""
                data, sr = eleven(text, voice, speed, prev_text, next_text)
            elif engine == "kokoro":
                data, sr = kokoro(text, voice, speed, lang)
            else:
                data, sr = piper(text, voice, speed)
            write_wav(wav, data, sr)
            duration = len(data) / sr
            status = "new"
        pause = float(seg.get("pause", 0.3))
        rows.append({"id": seg["id"], "text": text, "file": wav.name, "duration": round(duration, 3),
                     "pause": pause, "hash": h})
        total += duration + pause
        words = len(text.split())
        print(f"  {seg['id']:<18} {duration:6.2f}s  {words:3d} words  {words / duration * 60 if duration else 0:4.0f} wpm  {status}",
              flush=True)

    manifest = {"engine": engine, "voice": voice, "lang": lang, "speed": speed,
                "total": round(total, 3), "segments": rows}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"total {total:.1f}s -> {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
