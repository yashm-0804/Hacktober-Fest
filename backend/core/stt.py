"""Speech-to-text for the voice symptom check, using open-source faster-whisper on the CPU.

Gemma 4 via the Gemini API does not accept audio, so Whisper turns speech into text and Gemma reasons
over the text. transcribe() never raises; it returns {"text", "language", "seconds", "error"}.
Model: env WHISPER_MODEL (default "base"), device cpu, compute_type int8, loaded once per process.
"""
from __future__ import annotations

import io
import os
import time
from functools import lru_cache

LANGS = ("en", "hi")  # the demo audience speaks English, Hindi or Hinglish
MIN_SAMPLES = 1600  # 0.1 s at 16 kHz
# Without a Devanagari prompt, Whisper "hi" output drifts into Urdu script or romanised text, which the
# Hindi red-flag rules can't match. Measured on macOS `say -v Lekha` clips with the base model.
HINDI_PROMPT = "मरीज़ हिंदी में अपने लक्षण बता रहा है: बुखार, सिर दर्द, सीने में दर्द, सांस लेने में तकलीफ।"


def model_name() -> str:
    return (os.environ.get("WHISPER_MODEL") or "base").strip()


@lru_cache(maxsize=2)
def _model(name: str):
    from faster_whisper import WhisperModel

    return WhisperModel(name, device="cpu", compute_type="int8")


def _pick_language(model, audio) -> str | None:
    """Auto-detect, but restricted to English/Hindi: plain Whisper often labels Hindi speech as Urdu
    and then writes it in Urdu script."""
    try:
        _, _, probs = model.detect_language(audio=audio)
        probs = dict(probs)
        return max(LANGS, key=lambda lang: probs.get(lang, 0.0))
    except Exception:  # noqa: BLE001 - fall back to Whisper's own detection
        return None


def _decode_wav(wav_bytes: bytes):
    """PCM WAV -> float32 mono 16 kHz numpy array, decoded with the stdlib `wave` module (no PyAV needed)."""
    import wave

    import numpy as np

    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        rate, ch, width, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if width == 1:
        a = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128.0) / 128.0
    elif width == 2:
        a = np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0
    elif width == 4:
        a = np.frombuffer(raw, "<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width {width}")
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1)
    if rate != 16000 and len(a):
        new_len = int(round(len(a) * 16000 / rate))
        a = np.interp(np.linspace(0, len(a) - 1, new_len), np.arange(len(a)), a).astype(np.float32)
    return a


def _decode_av(audio_bytes: bytes):
    """Compressed audio (m4a/AAC from iOS and Android, webm/Opus from browsers) -> float32 mono 16 kHz.
    Calls PyAV directly: faster_whisper.audio.decode_audio passes an argument av 19 no longer accepts."""
    import av
    import numpy as np

    chunks = []
    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    with av.open(io.BytesIO(audio_bytes), mode="r") as container:
        stream = next(s for s in container.streams if s.type == "audio")
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray().reshape(-1))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32) / 32768.0


def _decode(audio_bytes: bytes):
    try:
        return _decode_wav(audio_bytes)
    except Exception:  # noqa: BLE001 - not a PCM WAV: decode it with PyAV
        try:
            return _decode_av(audio_bytes)
        except Exception as e:  # noqa: BLE001
            raise ValueError("could not read the audio (expected WAV, m4a or webm)") from e


def transcribe(wav_bytes: bytes) -> dict:
    t0 = time.time()
    out = {"text": "", "language": None, "seconds": 0.0, "error": None}
    try:
        if not wav_bytes:
            out["error"] = "No audio recorded."
            return out
        audio = _decode(wav_bytes)
        if audio is None or len(audio) < MIN_SAMPLES:
            out["error"] = "The recording is too short. Try again, or type instead."
            return out
        model = _model(model_name())
        lang = _pick_language(model, audio)
        segments, info = model.transcribe(audio, language=lang, vad_filter=True, condition_on_previous_text=False,
                                          initial_prompt=HINDI_PROMPT if lang == "hi" else None)
        text = " ".join(s.text.strip() for s in segments).strip()
        out["text"] = text
        out["language"] = lang or getattr(info, "language", None)
        if not text:
            out["error"] = "We didn't catch any speech. Try again closer to the mic, or type instead."
    except Exception as e:  # noqa: BLE001 - never raise into the UI
        out["error"] = f"Speech-to-text failed: {type(e).__name__}: {e}"[:300]
    finally:
        out["seconds"] = round(time.time() - t0, 2)
    return out
