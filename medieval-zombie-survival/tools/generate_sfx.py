#!/usr/bin/env python3
"""Procedural retro sound effects for Medieval Zombie Survival.

Writes 16-bit mono WAVs into ../assets/sfx/. Pure stdlib.
"""
import math
import os
import random
import struct
import wave

RATE = 22050
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "assets", "sfx")
random.seed(7)


def write_wav(name, samples):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        frames = b"".join(struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32000)) for s in samples)
        w.writeframes(frames)
    print("wrote sfx/%s.wav" % name)


def env(t, dur, attack=0.01, release=None):
    release = release if release is not None else dur * 0.7
    if t < attack:
        return t / attack
    if t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0


def lowpass(samples, alpha):
    out = []
    acc = 0.0
    for s in samples:
        acc += alpha * (s - acc)
        out.append(acc)
    return out


def noise_sound(dur, alpha_start, alpha_end, vol=0.6, attack=0.01):
    n = int(dur * RATE)
    raw = [random.uniform(-1, 1) for _ in range(n)]
    out = []
    acc = 0.0
    for i, s in enumerate(raw):
        t = i / RATE
        a = alpha_start + (alpha_end - alpha_start) * (i / n)
        acc += a * (s - acc)
        out.append(acc * env(t, dur, attack) * vol)
    return out


def tone(dur, f0, f1=None, vol=0.5, wave_kind="sine", vibrato=0.0, attack=0.01, release=None):
    f1 = f1 if f1 is not None else f0
    n = int(dur * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = f0 + (f1 - f0) * (i / n)
        if vibrato:
            f *= 1.0 + 0.03 * math.sin(t * vibrato * math.tau)
        phase += f / RATE
        if wave_kind == "sine":
            s = math.sin(phase * math.tau)
        elif wave_kind == "square":
            s = 1.0 if math.sin(phase * math.tau) > 0 else -1.0
        else:  # triangle
            s = 2.0 * abs(2.0 * (phase % 1.0) - 1.0) - 1.0
        out.append(s * env(t, dur, attack, release) * vol)
    return out


def mix(*tracks):
    n = max(len(t) for t in tracks)
    out = [0.0] * n
    for t in tracks:
        for i, s in enumerate(t):
            out[i] += s
    peak = max(1.0, max(abs(s) for s in out))
    return [s / peak * 0.9 for s in out]


def concat(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def main():
    write_wav("swing", noise_sound(0.16, 0.12, 0.5, vol=0.5, attack=0.04))
    write_wav("hit", mix(noise_sound(0.12, 0.5, 0.15, vol=0.7),
                         tone(0.14, 110, 60, vol=0.7)))
    write_wav("bow", mix(tone(0.12, 420, 180, vol=0.5, wave_kind="triangle"),
                         noise_sound(0.05, 0.6, 0.3, vol=0.35)))
    write_wav("magic", mix(tone(0.3, 320, 880, vol=0.4, vibrato=9),
                           tone(0.3, 640, 1760, vol=0.18, vibrato=9)))
    write_wav("frost", mix(tone(0.28, 900, 320, vol=0.35, vibrato=12),
                           noise_sound(0.28, 0.7, 0.4, vol=0.2)))
    write_wav("hurt", tone(0.18, 260, 120, vol=0.6, wave_kind="square"))
    write_wav("zombie", mix(tone(0.55, 95, 70, vol=0.55, vibrato=5, attack=0.1),
                            noise_sound(0.55, 0.08, 0.12, vol=0.3, attack=0.1)))
    write_wav("zombie_hit", mix(noise_sound(0.1, 0.4, 0.2, vol=0.6),
                                tone(0.12, 140, 90, vol=0.5)))
    write_wav("build", concat(mix(noise_sound(0.06, 0.6, 0.3, vol=0.6), tone(0.07, 180, 120, vol=0.6)),
                              [0.0] * int(0.06 * RATE),
                              mix(noise_sound(0.06, 0.6, 0.3, vol=0.5), tone(0.07, 160, 110, vol=0.5))))
    write_wav("pickup", concat(tone(0.06, 620, 660, vol=0.4, wave_kind="triangle"),
                               tone(0.08, 880, 920, vol=0.4, wave_kind="triangle")))
    write_wav("craft", concat(mix(noise_sound(0.05, 0.6, 0.3, vol=0.5), tone(0.06, 200, 150, vol=0.5)),
                              tone(0.1, 740, 780, vol=0.35, wave_kind="triangle")))
    write_wav("levelup", concat(tone(0.1, 523, 523, vol=0.4, wave_kind="triangle"),
                                tone(0.1, 659, 659, vol=0.4, wave_kind="triangle"),
                                tone(0.2, 784, 784, vol=0.45, wave_kind="triangle", release=0.15)))
    write_wav("explosion", mix(noise_sound(0.5, 0.35, 0.05, vol=0.9),
                               tone(0.45, 90, 40, vol=0.7)))
    write_wav("eat", concat(noise_sound(0.05, 0.3, 0.2, vol=0.4),
                            [0.0] * int(0.05 * RATE),
                            noise_sound(0.06, 0.3, 0.2, vol=0.35)))
    write_wav("door", mix(noise_sound(0.18, 0.2, 0.4, vol=0.4),
                          tone(0.18, 140, 200, vol=0.3, wave_kind="triangle")))
    # seamless-ish rain loop: steady filtered noise
    rain = noise_sound(2.0, 0.25, 0.25, vol=0.35, attack=0.0)
    n_fade = int(0.1 * RATE)
    for i in range(n_fade):  # crossfade tail into head for looping
        t = i / n_fade
        rain[i] = rain[i] * t + rain[len(rain) - n_fade + i] * (1 - t)
    write_wav("rain", rain[:len(rain) - n_fade])
    print("done")


if __name__ == "__main__":
    main()
