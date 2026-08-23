"""Local macOS double-clap activation companion.

Uses an adaptive, medium-sensitivity transient detector. Raw microphone audio never
leaves the Mac and is never sent to Gemini.
"""
from __future__ import annotations

import math
import os
import struct
import time
from collections import deque

import pyaudio
import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(ROOT, ".env"))

API = os.getenv("CLAP_API_URL", "http://127.0.0.1:8000/activation/clap")
BRIDGE_SECRET = os.getenv("SABA_CREATOR_ACTIVATION_SECRET", "")
RATE = 16000
CHUNK = 320  # 20 ms
CHANNELS = 1
MIN_GAP = max(0.16, int(os.getenv("CLAP_MIN_GAP_MS", "180")) / 1000.0)
MAX_GAP = min(0.85, int(os.getenv("CLAP_MAX_GAP_MS", "700")) / 1000.0)
HIT_REFRACTORY = 0.18
COOLDOWN = 4.0
WARMUP_SECONDS = 5.0
QUIET_RMS_MAX = float(os.getenv("CLAP_QUIET_RMS_MAX", "0.025"))
PEAK_THRESHOLD_MIN = float(os.getenv("CLAP_PEAK_THRESHOLD_MIN", "0.12"))
RMS_THRESHOLD_MIN = float(os.getenv("CLAP_RMS_THRESHOLD_MIN", "0.018"))
CREST_MIN = float(os.getenv("CLAP_CREST_MIN", "3.0"))
NOISE_MULTIPLIER = float(os.getenv("CLAP_NOISE_MULTIPLIER", "3.0"))
PEAK_NOISE_MULTIPLIER = float(os.getenv("CLAP_PEAK_NOISE_MULTIPLIER", "2.6"))



def samples(data: bytes):
    return struct.unpack("<" + "h" * (len(data) // 2), data)


def peak_abs(data: bytes) -> float:
    vals = samples(data)
    return max((abs(s) for s in vals), default=0) / 32768.0


def rms(data: bytes) -> float:
    vals = samples(data)
    if not vals:
        return 0.0
    return math.sqrt(sum(s * s for s in vals) / len(vals)) / 32768.0


def main():
    if not BRIDGE_SECRET:
        raise SystemExit("SABA_CREATOR_ACTIVATION_SECRET is missing from .env")

    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    hits = deque(maxlen=4)
    floor_samples = deque(maxlen=150)
    peak_floor_samples = deque(maxlen=150)
    last_activation = 0.0
    last_hit = 0.0
    start = time.monotonic()
    print("Saba clap companion online. Calibrating… strict double-clap mode.")

    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            level = rms(data)
            peak = peak_abs(data)
            now = time.monotonic()

            if now - start < WARMUP_SECONDS:
                floor_samples.append(level)
                peak_floor_samples.append(peak)
                continue

            noise = sorted(floor_samples)[max(0, int(len(floor_samples) * 0.85) - 1)] if floor_samples else 0.01
            peak_noise = sorted(peak_floor_samples)[max(0, int(len(peak_floor_samples) * 0.85) - 1)] if peak_floor_samples else 0.035

            # Hardened detector: a clap must be a short, high-crest transient
            # above an adaptive floor, while ordinary speech/music/room noise
            # is rejected by the quiet-gate and stronger thresholds.
            rms_threshold = max(RMS_THRESHOLD_MIN, noise * NOISE_MULTIPLIER + 0.008)
            peak_threshold = max(PEAK_THRESHOLD_MIN, peak_noise * PEAK_NOISE_MULTIPLIER + 0.035)
            crest = peak / max(level, 0.001)
            quiet_gate = level <= max(QUIET_RMS_MAX, noise * 2.2 + 0.004)
            is_hit = (
                peak >= peak_threshold
                and level >= rms_threshold * 0.70
                and crest >= CREST_MIN
                and quiet_gate
            )

            if is_hit:
                if now - last_hit >= HIT_REFRACTORY:
                    last_hit = now
                    hits.append(now)
                    if len(hits) >= 2:
                        gap = hits[-1] - hits[-2]
                        if MIN_GAP <= gap <= MAX_GAP and now - last_activation >= COOLDOWN:
                            try:
                                r = requests.post(
                                    API,
                                    json={"role": "creator"},
                                    headers={"X-Bridge-Secret": BRIDGE_SECRET},
                                    timeout=2,
                                )
                                r.raise_for_status()
                                print(f"Double clap detected → creator activated. rms={level:.3f} peak={peak:.3f}")
                            except Exception as exc:
                                print(f"Activation bridge unavailable: {exc}")
                            last_activation = now
                            hits.clear()
                # A transient (even one inside the refractory window) is never
                # "room noise" - never fold it into the adaptive floor, or the
                # floor creeps up after real claps and the detector gets less
                # sensitive right when it's being used.
            else:
                # Keep the floor adaptive when no transient is present.
                floor_samples.append(level)
                peak_floor_samples.append(peak)

    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()


if __name__ == "__main__":
    main()
