#!/usr/bin/env python3
"""Bande-son d'effets de la vidéo My_AI 9.1.0 (46 s, 48 kHz, stéréo), calée sur la
timeline du prompt : pop + gouttes, clics, frappe au clavier, envois, succès, fin.
Écrit sons/bande_son_sfx.wav et sons/reperes_sons.txt."""

import os
import sys
import wave

import numpy as np

OUT = sys.argv[1]
SR = 48000
DURATION = 46.0
rng = np.random.default_rng(11)


def env(n, attack, tau):
    t = np.arange(n) / SR
    return np.clip(t / attack, 0, 1) * np.exp(-t / tau)


def bloop(dur=0.16, f0=1150, f1=300, sweep=0.07, tau=0.04):
    n = int(SR * dur)
    t = np.arange(n) / SR
    k = np.clip(t / sweep, 0, 1)
    freq = f1 + (f0 - f1) * np.exp(-4.0 * k)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    tone = np.sin(phase) + 0.25 * np.sin(2 * phase) + 0.08 * np.sin(3 * phase)
    click = rng.standard_normal(n) * env(n, 0.0002, 0.0018) * 0.35
    return tone * env(n, 0.0015, tau) + click


def blip(freq, dur=0.05, tau=0.012, gain=0.25):
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 2.01 * t)
    return tone * env(n, 0.0008, tau) * gain


def pop_gouttes():
    track = np.zeros(int(SR * 0.62))
    add(track, bloop(), 0.0)
    for i, (f, at) in enumerate([(2350, 0.085), (2950, 0.13), (2600, 0.18), (3300, 0.235),
                                 (2800, 0.29), (3600, 0.35)]):
        add(track, blip(f, gain=0.22 * (0.85 ** i)), at)
    return track


def clic(gain=0.5):
    n = int(SR * 0.045)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1900 * t) * 0.6 + rng.standard_normal(n) * 0.25) * env(n, 0.0003, 0.006) * gain


def touche(gain=0.12):
    """Une touche de clavier : petit bruit sec et un léger choc grave."""
    n = int(SR * 0.03)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    noise = noise - np.convolve(noise, np.ones(6) / 6, mode='same')  # passe-haut grossier
    thump = np.sin(2 * np.pi * rng.uniform(170, 240) * t) * env(n, 0.0005, 0.008) * 0.5
    return (noise * env(n, 0.0002, 0.0035) + thump) * gain * rng.uniform(0.7, 1.0)


def frappe(seconds):
    n = int(SR * seconds)
    track = np.zeros(n + SR // 10)
    at = 0.0
    while at < seconds:
        add(track, touche(), at)
        at += rng.uniform(0.065, 0.13)
    return track


def envoi(gain=0.32):
    n = int(SR * 0.28)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    smooth = np.convolve(noise, np.ones(24) / 24, mode='same')
    return smooth * np.sin(np.pi * np.clip(t / 0.28, 0, 1)) ** 2 * gain * 3


def note(freq, dur, tau, gain):
    n = int(SR * dur)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * freq * t) + 0.18 * np.sin(2 * np.pi * freq * 2 * t) + 0.05 * np.sin(2 * np.pi * freq * 3 * t)
    return tone * env(n, 0.004, tau) * gain


def succes():
    track = np.zeros(int(SR * 0.7))
    add(track, note(880.0, 0.5, 0.12, 0.18), 0.0)
    add(track, note(1318.5, 0.6, 0.16, 0.18), 0.11)
    return track


def fin():
    track = np.zeros(int(SR * 2.2))
    for i, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        add(track, note(f, 2.0, 0.55, 0.11), i * 0.06)
    return track


def add(track, sig, at):
    i = int(SR * at)
    j = min(len(track), i + len(sig))
    track[i:j] += sig[:j - i]
    return track


# (temps en s, nom, signal) : la même timeline que le prompt
CUES = [
    (6.75, "pop + gouttes (le bouton Code apparaît)", pop_gouttes()),
    (10.40, "clic sur Code", clic()),
    (12.80, "frappe au clavier sur le PC (1,2 s)", frappe(1.2)),
    (14.20, "envoi du message du PC", envoi()),
    (16.40, "clic sur « Autoriser une fois » (PC)", clic()),
    (18.80, "frappe au clavier dans VS Code (1,0 s)", frappe(1.0)),
    (20.00, "envoi du message de VS Code", envoi()),
    (21.80, "clic sur « Autoriser une fois » (VS Code)", clic()),
    (27.90, "toucher sur </> (téléphone)", clic(0.4)),
    (30.60, "envoi du message du téléphone", envoi()),
    (33.40, "toucher sur « Autoriser une fois » (téléphone)", clic(0.4)),
    (35.40, "succès : les 4 tests passent", succes()),
    (37.80, "le message de VS Code arrive sur le téléphone", envoi()),
    (43.00, "carte de fin", fin()),
]

track = np.zeros(int(SR * DURATION))
for at, _label, sig in CUES:
    add(track, sig, at)
track = track / (np.max(np.abs(track)) + 1e-9) * 10 ** (-3 / 20)
stereo = np.stack([track, track], axis=1)
data = (stereo * 32767).astype('<i2')
with wave.open(os.path.join(OUT, 'bande_son_sfx.wav'), 'wb') as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(data.tobytes())

lines = ["Repères de la bande-son d'effets (bande_son_sfx.wav, 46 s) : à poser à 0:00 sous la vidéo.",
         "Si la vidéo ne suit pas exactement la timeline, placez les sons à la main à ces temps :", ""]
for at, label, _sig in CUES:
    lines.append(f"{int(at // 60)}:{at % 60:05.2f}  {label}")
lines += ["", "Sons séparés : pop.wav, pop_gouttes.wav, clic.wav, envoi.wav."]
with open(os.path.join(OUT, 'reperes_sons.txt'), 'w', encoding='utf-8') as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines))
