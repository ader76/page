#!/usr/bin/env python3
"""Génère la voix off (une piste WAV par section) avec Piper, et écrit les durées.

Usage : <venv>/bin/python tools/film/voice.py --models /tmp/tts --out /tmp/film/voice [fr en zh ar]
Sortie : <out>/<lang>/sNN.wav et <out>/<lang>/durations.json
"""
import argparse, json, os, subprocess, sys, wave

ap = argparse.ArgumentParser()
ap.add_argument("--models", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("langs", nargs="*", default=["fr", "en", "zh", "ar"])
a = ap.parse_args()

here = os.path.dirname(os.path.abspath(__file__))
N = json.load(open(os.path.join(here, "narration.json"), encoding="utf-8"))
piper = os.path.join(os.path.dirname(sys.executable), "piper")

for lang in a.langs:
    model = os.path.join(a.models, N["voices"][lang] + ".onnx")
    d = os.path.join(a.out, lang)
    os.makedirs(d, exist_ok=True)
    durs = []
    for i, text in enumerate(N[lang]):
        wav = os.path.join(d, "s%02d.wav" % i)
        subprocess.run([piper, "-m", model, "-f", wav, "--length-scale", str(N.get("speed", {}).get(lang, 1.0)), "--sentence-silence", "0.35"],
                       input=text.encode("utf-8"), check=True, capture_output=True)
        with wave.open(wav) as w:
            durs.append(round(w.getnframes() / w.getframerate(), 2))
    json.dump(durs, open(os.path.join(d, "durations.json"), "w"))
    print(lang, durs, "total", round(sum(durs), 1))
