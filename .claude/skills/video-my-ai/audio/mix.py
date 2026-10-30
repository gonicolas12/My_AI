#!/usr/bin/env python3
"""Mixage final d'une vidéo My_AI : musique et effets posés sur le MP4 exporté
par Claude Motion.

Réglages validés avec la vidéo 9.1.0 : musique −3 dB, effets −4 dB, gain jusqu'à
−15 LUFS intégrés, limiteur à 0,82, AAC 192 kb/s, image copiée sans réencodage.

Usage : python3 mix.py VIDEO.mp4 MUSIQUE.wav EFFETS.wav SORTIE.mp4
"""

import json
import os
import re
import subprocess
import sys
import tempfile

MUSIC_DB = -3.0
SFX_DB = -4.0
TARGET_LUFS = -15.0


def ffmpeg(*args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], check=True,
                          capture_output=True, text=True).stderr


def integrated_loudness(path):
    report = ffmpeg("-i", path, "-af", "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json",
                    "-f", "null", "-")
    return float(json.loads(report[report.rindex("{"):])["input_i"])


video, music, sfx, output = sys.argv[1:5]
with tempfile.TemporaryDirectory() as tmp:
    premix = os.path.join(tmp, "premix.wav")
    ffmpeg("-v", "error", "-i", music, "-i", sfx, "-filter_complex",
           f"[0:a]volume={MUSIC_DB}dB[m];[1:a]volume={SFX_DB}dB[s];"
           "[m][s]amix=inputs=2:normalize=0:duration=longest[a]",
           "-map", "[a]", "-ar", "48000", "-c:a", "pcm_f32le", "-y", premix)
    gain = TARGET_LUFS - integrated_loudness(premix)
    final = os.path.join(tmp, "mix.wav")
    ffmpeg("-v", "error", "-i", premix, "-af",
           f"volume={gain:.2f}dB,alimiter=limit=0.82:attack=4:release=60:level=0,aresample=48000",
           "-c:a", "pcm_s24le", "-y", final)
    ffmpeg("-v", "error", "-i", video, "-i", final, "-map", "0:v", "-map", "1:a",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
           "-movflags", "+faststart", "-y", output)

summary = ffmpeg("-i", output, "-af", "ebur128=peak=true", "-f", "null", "-")
summary = summary[summary.rindex("Summary:"):]
lufs = re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1)
peak = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary).group(1)
print(f"{output} : {lufs} LUFS intégrés, crête vraie {peak} dBFS (gain appliqué {gain:+.1f} dB)")
