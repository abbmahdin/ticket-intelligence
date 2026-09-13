#!/usr/bin/env python3
"""Transcription de toutes les videos du dossier V avec whisper (GPU)."""
import os, glob, subprocess, sys, time

SRC = "/mnt/c/Users/redou/OneDrive/Bureau/V"
OUT = "/tmp/transcripts_V"
FF = os.path.expanduser("~/QuantLive/.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2")
PY = os.path.expanduser("~/QuantLive/.venv/bin/python")

os.makedirs(OUT, exist_ok=True)

videos = sorted(glob.glob(os.path.join(SRC, "*.MP4")))
total = len(videos)
print(f"Total videos: {total}", flush=True)

import whisper
model = whisper.load_model("small")  # GPU cuda auto

done = 0
for i, vp in enumerate(videos, 1):
    base = os.path.splitext(os.path.basename(vp))[0]
    txt = os.path.join(OUT, base + ".txt")
    wav = os.path.join(OUT, base + ".wav")
    if os.path.exists(txt):
        print(f"[{i}/{total}] DEJA FAIT: {base}", flush=True)
        done += 1
        continue
    t0 = time.time()
    # extrait audio
    subprocess.run([FF, "-y", "-i", vp, "-ar", "16000", "-ac", "1", "-vn", wav],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # transcrit
    r = model.transcribe(wav, language="en", fp16=True, verbose=False)
    with open(txt, "w") as f:
        f.write(r["text"].strip())
    os.remove(wav)
    dt = time.time() - t0
    done += 1
    print(f"[{i}/{total}] OK {base} ({dt:.0f}s) | cumul={done}", flush=True)

print(f"FIN: {done}/{total} videos transcrites dans {OUT}", flush=True)
