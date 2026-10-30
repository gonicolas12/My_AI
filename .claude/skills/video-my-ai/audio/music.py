#!/usr/bin/env python3
"""Musique originale de la vidéo My_AI 9.1.0 (46 s), calée sur le montage.

Do majeur, 105,93 BPM : une mesure = 2,265625 s, si bien que le premier temps de
la mesure 3 tombe sur le pop (6,75 s) et celui de la mesure 19 sur la carte de
fin (43,0 s). Piano, nappe, cordes et vibraphone rendus par FluidSynth
(FluidR3_GM) ; batterie, basse, montées et impact synthétisés ici.

Structure (mesures) :
  0-2   intro : Am9 | Fmaj9 | Gsus4 G, nappe qui s'ouvre, montée vers le pop
  3-10  groove : C | G | Am | F (x2), piano en croches ; mélodie au vibraphone en 7-10
  11-12 respiration (le téléphone entre) : sans grosse caisse
  13-17 groove complet, cordes à partir de 15
  18    F G sans batterie, montée vers la fin
  19    Cadd9 final, qui s'éteint jusqu'à 46 s

Usage : python3 music.py DOSSIER_SORTIE
"""

import os
import subprocess
import sys

import mido
import numpy as np
from scipy import signal
from scipy.io import wavfile

OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
SR = 48000
BAR = 2.265625
BEAT = BAR / 4
OFFSET = 3 * BAR - 6.75          # la mesure 0 commence 0,046875 s avant 0:00
TOTAL = 46.0
RENDER = TOTAL + OFFSET + 3.0     # marge pour les queues de notes
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
rng = np.random.default_rng(2026)

# ── Harmonie ───────────────────────────────────────────────────────────────
# Accord par mesure (0 à 19). La mesure 18 est partagée : F (2 temps) puis G.
CYCLE = ["C", "G", "Am", "F"]
CHORDS = ["Am9", "Fmaj9", "Gsus"] + CYCLE * 4
CHORDS[18] = "FG"
CHORDS.append("Cadd9")  # mesure 19

PAD = {
    # Intro sans notes voisines d'un demi-ton : Am7, Fmaj7, puis Gsus4 qui se résout en G
    "Am9": [57, 60, 64, 67], "Fmaj9": [53, 57, 60, 64], "Gsus": [55, 62, 67, 72],
    "G_resolved": [55, 62, 67, 71], "C": [52, 55, 60, 64], "G": [50, 55, 59, 62],
    "Am": [52, 57, 60, 64], "F": [53, 57, 60, 65], "Cadd9": [48, 55, 60, 64, 67, 72],
}
ARP = {
    "C": [60, 64, 67, 72, 76], "G": [59, 62, 67, 71, 74], "Am": [57, 60, 64, 69, 72],
    "F": [57, 60, 65, 69, 72],
}
ROOT_HZ = {"Am9": 55.0, "Fmaj9": 43.65, "Gsus": 49.0, "C": 65.41, "G": 49.0, "Am": 55.0,
           "F": 43.65, "Cadd9": 65.41}
STRINGS = {"C": [67, 72, 76], "G": [67, 71, 74], "Am": [69, 72, 76], "F": [69, 72, 77],
           "G2": [71, 74, 79], "Cadd9": [60, 67, 72, 76, 79]}
# Mélodie (vibraphone) sur un cycle C G Am F : (temps dans la mesure, durée, note)
MELODY = {
    "C": [(0, 1.5, 76), (1.5, 0.5, 72), (2, 1, 67), (3, 1, 72)],
    "G": [(0, 1.5, 74), (1.5, 0.5, 71), (2, 2, 67)],
    "Am": [(0, 1, 72), (1, 1, 76), (2, 1, 81), (3, 1, 76)],
    "F": [(0, 1.5, 69), (1.5, 0.5, 72), (2, 2, 77)],
    "FG": [(0, 1, 69), (1, 1, 72), (2, 1, 71), (3, 1, 74)],
}


def beat_of(bar, beat=0.0):
    return bar * 4 + beat


# ── MIDI (une piste par instrument, rendue à part) ─────────────────────────
TPB = 960
TEMPO = int(round(BEAT * 1e6))


class Stem:
    def __init__(self, program):
        self.program = program
        self.events = []      # (beat, kind, data)

    def note(self, start, dur, pitch, vel, jitter=True):
        if jitter and start % 1:
            start += rng.uniform(-0.012, 0.012)
        vel = int(np.clip(vel + (rng.integers(-5, 6) if jitter else 0), 1, 127))
        self.events.append((max(0.0, start), 1, (pitch, vel)))
        self.events.append((start + dur, 0, (pitch, 0)))

    def cc(self, at, number, value):
        self.events.append((at, 2, (number, int(np.clip(value, 0, 127)))))

    def ramp(self, start, end, number, v0, v1, steps=24):
        for i in range(steps + 1):
            self.cc(start + (end - start) * i / steps, number, v0 + (v1 - v0) * i / steps)

    def write(self, path):
        mid = mido.MidiFile(ticks_per_beat=TPB)
        track = mido.MidiTrack()
        mid.tracks.append(track)
        track.append(mido.MetaMessage("set_tempo", tempo=TEMPO, time=0))
        track.append(mido.Message("program_change", program=self.program, channel=0, time=0))
        track.append(mido.Message("control_change", control=7, value=110, channel=0, time=0))
        now = 0
        for at, kind, data in sorted(self.events, key=lambda e: (e[0], e[1])):
            tick = int(round(at * TPB))
            delta = max(0, tick - now)
            now += delta
            if kind == 2:
                track.append(mido.Message("control_change", control=data[0], value=data[1],
                                          channel=0, time=delta))
            elif kind == 1:
                track.append(mido.Message("note_on", note=data[0], velocity=data[1],
                                          channel=0, time=delta))
            else:
                track.append(mido.Message("note_off", note=data[0], velocity=0,
                                          channel=0, time=delta))
        mid.save(path)


piano, pad, strings, vibes = Stem(4), Stem(89), Stem(48), Stem(11)   # piano électrique, plus doux

# Nappe : toute la vidéo, qui s'ouvre pendant l'intro et s'éteint à la fin
pad.ramp(0, beat_of(3), 11, 30, 100)
for bar, chord in enumerate(CHORDS):
    if chord == "Gsus":
        for p in PAD["Gsus"]:
            pad.note(beat_of(bar), 2, p, 52, jitter=False)
        for p in PAD["G_resolved"]:
            pad.note(beat_of(bar, 2), 2.0, p, 52, jitter=False)
    elif chord == "FG":
        for p in PAD["F"]:
            pad.note(beat_of(bar), 2, p, 52, jitter=False)
        for p in PAD["G"]:
            pad.note(beat_of(bar, 2), 2.0, p, 52, jitter=False)
    elif chord == "Cadd9":
        for p in PAD["Cadd9"]:
            pad.note(beat_of(bar), 7, p, 58, jitter=False)
    else:
        level = 44 if bar in (11, 12) else 52
        for p in PAD[chord]:
            pad.note(beat_of(bar), 4.0, p, level, jitter=False)
pad.ramp(beat_of(19, 2), beat_of(20, 2), 11, 100, 0)

# Piano : accords égrenés dans l'intro (aucune note ne déborde sur l'accord suivant ;
# en mesure 2, le do de Gsus4 s'arrête quand le si de G arrive), croches liées ensuite,
# noires pendant la respiration. Jeu doux : vélocités basses.
INTRO_PIANO = {
    0: [(0, 2, 57), (1, 2, 64), (2, 2, 67), (3, 1, 72)],        # Am7
    1: [(0, 2, 53), (1, 2, 60), (2, 2, 64), (3, 1, 69)],        # Fmaj7
    2: [(0, 2, 55), (1, 1, 72), (2, 2, 71), (3, 1, 74)],        # Gsus4 (do) puis G (si)
}
for bar, notes in INTRO_PIANO.items():
    for i, (beat, dur, p) in enumerate(notes):
        piano.note(beat_of(bar, beat), dur, p, 36 + 3 * i, jitter=False)
PATTERN = [0, 1, 2, 3, 4, 3, 2, 1]
for bar in range(3, 18):
    tones = ARP[CHORDS[bar]]
    if bar in (11, 12):
        for i, idx in enumerate([0, 2, 4, 2]):
            piano.note(beat_of(bar, i), 0.95, tones[idx], 42 if i else 46)
        continue
    for i, idx in enumerate(PATTERN):
        vel = 48 if i == 0 else (42 if i % 2 == 0 else 37)
        piano.note(beat_of(bar, i * 0.5), 0.5 if i == 7 else 0.9, tones[idx], vel)
for i, idx in enumerate([0, 1, 2, 3]):                          # mesure 18 : F puis G
    piano.note(beat_of(18, i * 0.5), 0.5 if i == 3 else 0.9, ARP["F"][idx], 40 + 2 * i)
for i, idx in enumerate([0, 1, 2, 4]):
    piano.note(beat_of(18, 2 + i * 0.5), 0.5 if i == 3 else 0.9, ARP["G"][idx], 44 + 2 * i)
for p, vel in zip([48, 55, 64, 67, 72, 76], [52, 46, 44, 44, 46, 42]):  # accord final
    piano.note(beat_of(19), 6.5, p, vel, jitter=False)

# Vibraphone : mélodie en 7-10 et 15-18, puis la tierce et la quinte finales
for bar in list(range(7, 11)) + list(range(15, 19)):
    for start, dur, p in MELODY[CHORDS[bar]]:
        vibes.note(beat_of(bar, start), dur * 0.95, p, 60 if start == 0 else 54)
for p in (72, 76):
    vibes.note(beat_of(19), 5, p, 56, jitter=False)

# Cordes : montent en 15-18, tiennent l'accord final
strings.cc(0, 11, 0)
for bar in range(15, 18):
    for p in STRINGS[CHORDS[bar]]:
        strings.note(beat_of(bar), 4.0, p, 70, jitter=False)
    strings.ramp(beat_of(bar), beat_of(bar, 3.5), 11, 55 + 8 * (bar - 15), 85 + 8 * (bar - 15), 12)
for p in STRINGS["F"]:
    strings.note(beat_of(18), 2, p, 76, jitter=False)
for p in STRINGS["G2"]:
    strings.note(beat_of(18, 2), 2.0, p, 80, jitter=False)
strings.ramp(beat_of(18), beat_of(19), 11, 80, 112, 16)
for p in STRINGS["Cadd9"]:
    strings.note(beat_of(19), 6.5, p, 74, jitter=False)
strings.ramp(beat_of(19, 1), beat_of(20, 2), 11, 112, 0, 24)


def sounding(stem):
    """Notes jouées : (début, fin, hauteur) en temps."""
    notes, open_ = [], {}
    for at, kind, data in sorted(stem.events, key=lambda e: (e[0], e[1])):
        if kind == 1:
            open_.setdefault(data[0], []).append(at)
        elif kind == 0 and open_.get(data[0]):
            notes.append((open_[data[0]].pop(0), at, data[0]))
    return notes


def check_clashes(named):
    """Demi-tons (ou neuvièmes mineures) joués en même temps : la « fausse note »."""
    notes = [(name, s, e, p) for name, stem in named.items() for s, e, p in sounding(stem)]
    found = []
    t, end = 0.0, max(e for _, _, e, _ in notes)
    while t < end:
        now = [(n, p) for n, s, e, p in notes if s <= t < e - 0.1]
        for i in range(len(now)):
            for j in range(i + 1, len(now)):
                if abs(now[i][1] - now[j][1]) in (1, 13):
                    found.append((round(t, 3), now[i], now[j]))
        t += 0.125
    return found


clashes = check_clashes({"piano": piano, "pad": pad, "cordes": strings, "vibraphone": vibes})
for t, a, b in clashes[:20]:
    print(f"FROTTEMENT temps {t} ({t * BEAT - OFFSET:.2f} s) : {a} contre {b}")
print("frottements d'un demi-ton :", len(clashes))
assert not clashes, "fausse note détectée"


def render(stem, name):
    mid_path = os.path.join(OUT, f"{name}.mid")
    wav_path = os.path.join(OUT, f"{name}.wav")
    stem.write(mid_path)
    subprocess.run(["fluidsynth", "-ni", "-q", "-g", "0.4", "-R", "0", "-C", "0",
                    "-r", str(SR), "-F", wav_path, SF2, mid_path], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sr, data = wavfile.read(wav_path)
    assert sr == SR, sr
    data = data.astype(np.float64)
    if data.dtype != np.float64 or np.abs(data).max() > 2:
        data /= 32768.0
    n = int(RENDER * SR)
    out = np.zeros((n, 2))
    m = min(n, len(data))
    out[:m] = data[:m] if data.ndim == 2 else np.stack([data[:m]] * 2, axis=1)
    return out


stems = {name: render(stem, name) for name, stem in
         (("piano", piano), ("pad", pad), ("strings", strings), ("vibes", vibes))}

# ── Synthèse : batterie, basse, montées, impact ───────────────────────────
N = int(RENDER * SR)
T = np.arange(N) / SR


def at_beat(beat):
    return beat * BEAT


def place(buf, sig, t):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i]


def env(n, attack, tau):
    t = np.arange(n) / SR
    return np.clip(t / max(attack, 1e-6), 0, 1) * np.exp(-t / tau)


def butter(kind, freq, order=2):
    return signal.butter(order, freq, btype=kind, fs=SR, output="sos")


def kick(gain=1.0):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    freq = 47 + (128 - 47) * np.exp(-t / 0.032)
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR) * env(n, 0.001, 0.22)
    click = signal.sosfilt(butter("highpass", 2500), rng.standard_normal(n)) * env(n, 0.0002, 0.003) * 0.5
    return np.tanh(1.6 * (body + click)) * gain


def hat(open_=False, gain=1.0):
    n = int((0.32 if open_ else 0.09) * SR)
    noise = signal.sosfilt(butter("highpass", 7200, 4), rng.standard_normal(n))
    return noise * env(n, 0.0005, 0.11 if open_ else 0.022) * gain


def clap(gain=1.0):
    n = int(0.35 * SR)
    noise = signal.sosfilt(butter("bandpass", [900, 3200], 2), rng.standard_normal(n))
    shape = np.zeros(n)
    for k, d in enumerate((0.0, 0.011, 0.021)):
        i = int(d * SR)
        shape[i:] += env(n - i, 0.0005, 0.006 if k < 2 else 0.11)
    return noise * shape * gain


def sweep(duration, f0, f1, rising=True, gain=1.0):
    """Bruit filtré dont la bande glisse de f0 à f1 (montée ou descente)."""
    n = int(duration * SR)
    noise = rng.standard_normal(n)
    out = np.zeros(n)
    block = 1024
    zi = None
    for b in range(0, n, block):
        frac = b / n
        fc = f0 * (f1 / f0) ** frac
        sos = signal.butter(2, [max(40, fc * 0.6), min(SR / 2 - 100, fc * 1.6)],
                            btype="bandpass", fs=SR, output="sos")
        if zi is None or zi.shape != (sos.shape[0], 2):
            zi = signal.sosfilt_zi(sos) * 0
        out[b:b + block], zi = signal.sosfilt(sos, noise[b:b + block], zi=zi)
    t = np.arange(n) / n
    shape = t ** 2.2 if rising else (1 - t) ** 1.6
    fade = np.ones(n)
    k = int(0.03 * SR)
    fade[-k:] = np.linspace(1, 0, k)
    return out * shape * fade * gain


def impact(gain=1.0):
    n = int(1.4 * SR)
    t = np.arange(n) / SR
    boom = np.sin(2 * np.pi * (52 + 30 * np.exp(-t / 0.05)) * t) * env(n, 0.002, 0.55)
    air = signal.sosfilt(butter("lowpass", 1800), rng.standard_normal(n)) * env(n, 0.001, 0.25) * 0.35
    return (boom + air) * gain


drums = np.zeros(N)
hats = np.zeros(N)
fx = np.zeros(N)
kick_env = np.zeros(N)
kick_bars = list(range(3, 11)) + list(range(13, 18))
clap_bars = list(range(5, 11)) + list(range(14, 18))
hat_bars = list(range(3, 18))
for bar in kick_bars:
    for b in (0, 2):
        t = at_beat(beat_of(bar, b))
        place(drums, kick(0.9), t)
        place(kick_env, env(int(0.4 * SR), 0.001, 0.16), t)
    if bar in (6, 10, 17):
        place(drums, kick(0.55), at_beat(beat_of(bar, 3.5)))
for bar in clap_bars:
    for b in (1, 3):
        place(drums, clap(0.32), at_beat(beat_of(bar, b)))
for bar in hat_bars:
    soft = 0.45 if bar in (11, 12) else 1.0
    for i in range(8):
        accent = 0.22 if i % 2 else 0.12
        place(hats, hat(gain=accent * soft * rng.uniform(0.85, 1.0)), at_beat(beat_of(bar, i * 0.5)))
    if bar in (6, 10, 14, 17):
        place(hats, hat(True, 0.16 * soft), at_beat(beat_of(bar, 3.5)))
place(fx, sweep(BAR * 0.98, 320, 7000, True, 0.55), at_beat(beat_of(2)))       # montée vers le pop
place(fx, impact(0.9), at_beat(beat_of(3)))                                    # impact au pop
place(fx, sweep(BAR * 0.6, 6500, 350, False, 0.3), at_beat(beat_of(11)))       # redescente (téléphone)
place(fx, sweep(BAR * 0.98, 300, 6000, True, 0.4), at_beat(beat_of(18)))       # montée vers la fin
place(fx, impact(0.5), at_beat(beat_of(19)))

# Basse : sinus + harmoniques, une note par mesure (deux en 18), relancée sur le « et » du 2
bass = np.zeros(N)
segments = []
for bar, chord in enumerate(CHORDS):
    if chord == "FG":
        segments.append((beat_of(bar), 2, ROOT_HZ["F"]))
        segments.append((beat_of(bar, 2), 2, ROOT_HZ["G"]))
    elif chord == "Cadd9":
        segments.append((beat_of(bar), 6, ROOT_HZ["Cadd9"]))
    else:
        segments.append((beat_of(bar), 4, ROOT_HZ[chord]))
for start, dur, hz in segments:
    n = int(at_beat(dur) * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * hz * t) + 0.3 * np.sin(4 * np.pi * hz * t) + 0.1 * np.sin(6 * np.pi * hz * t)
    shape = np.minimum(np.clip(t / 0.012, 0, 1), np.clip((t[-1] - t) / 0.06, 0, 1))
    if start >= beat_of(19):
        shape *= np.exp(-t / 1.6)
    if start < beat_of(3):
        shape *= np.clip((at_beat(start) + t) / at_beat(beat_of(3)), 0.15, 1) * 0.6
    place(bass, np.tanh(1.3 * tone) * shape, at_beat(start))

# ── Mixage ────────────────────────────────────────────────────────────────


def rms(x):
    return float(np.sqrt(np.mean(np.square(x[np.abs(x) > 1e-5])))) if np.any(np.abs(x) > 1e-5) else 1.0


def stereo(mono, width=0.0):
    if mono.ndim == 2:
        return mono
    return np.stack([mono * (1 - width), mono * (1 + width)], axis=1) / (1 + width)


def reverb_ir(seconds=2.6, rt60=2.3, predelay=0.025):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = np.zeros((n, 2))
    for c in range(2):
        noise = rng.standard_normal(n)
        dark = signal.sosfilt(butter("lowpass", 2500), noise)
        mix = noise * np.exp(-t / 0.35) + dark * (1 - np.exp(-t / 0.35))
        ir[:, c] = mix * np.exp(-6.9 * t / rt60)
    ir[: int(predelay * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2, axis=0))


IR = reverb_ir()


def reverb(x):
    wet = np.zeros_like(x)
    for c in range(2):
        wet[:, c] = signal.fftconvolve(x[:, c], IR[:, c])[: len(x)]
    return wet


duck = 1 - 0.45 * np.clip(kick_env, 0, 1)
duck_soft = 1 - 0.25 * np.clip(kick_env, 0, 1)

# (signal stéréo, niveau RMS visé en dB, part de réverb, ducking)
layers = {
    "pad": (stems["pad"], -27, 0.25, duck),
    "piano": (signal.sosfilt(butter("lowpass", 4200), stems["piano"], axis=0), -30, 0.38, duck_soft),
    "strings": (stems["strings"], -29, 0.35, duck),
    "vibes": (stems["vibes"], -29, 0.40, None),
    "bass": (stereo(bass), -25, 0.0, duck),
    "drums": (stereo(drums), -23, 0.08, None),
    "hats": (np.stack([hats * 0.9, hats * 1.1], axis=1), -34, 0.10, None),
    "fx": (stereo(fx, 0.1), -30, 0.35, None),
}
mix = np.zeros((N, 2))
for name, (sig, level_db, wet, ducking) in layers.items():
    sig = sig * (10 ** (level_db / 20) / rms(sig))
    if ducking is not None:
        sig = sig * ducking[:, None]
    mix += sig * (1 - wet * 0.3) + reverb(sig) * wet
    print(f"{name:8s} rms visé {level_db} dB, réverb {wet:.2f}")

mix = signal.sosfilt(butter("highpass", 30), mix, axis=0)
start = int(round(OFFSET * SR))                    # la mesure 3 tombe à 6,75 s
mix = mix[start:start + int(TOTAL * SR)]
fade = int(1.4 * SR)
mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
mix[: int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))[:, None]
mix = np.tanh(mix / 0.9) * 0.9                     # écrêtage doux, au cas où
mix *= 10 ** (-1.0 / 20) / np.max(np.abs(mix))
wavfile.write(os.path.join(OUT, "musique.wav"), SR, mix.astype(np.float32))
print("musique.wav", f"{len(mix) / SR:.2f} s")
