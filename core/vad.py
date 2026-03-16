"""
Voice Activity Detection + Speech Accumulation

Fixes for missing voice:
  1. Lower default threshold (0.008 vs 0.015) catches quiet speech
  2. Overlap/lookback buffer means no words lost at chunk boundaries
  3. RMS normalization boosts quiet mic input before Whisper sees it
  4. Minimum speech duration prevents tiny hallucination-prone clips
  5. Silence padding gives Whisper context at start/end of each segment
"""
from __future__ import annotations
import os
import numpy as np
from typing import Optional

_TARGET_RMS = 0.08   # ~-22 dBFS — loud enough for Whisper without clipping


def normalize_audio(audio: np.ndarray, target_rms: float = _TARGET_RMS) -> np.ndarray:
    """Scale audio RMS to target_rms. Most impactful fix for quiet microphones."""
    rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    if rms < 1e-6:
        return audio
    gain = min(target_rms / rms, 20.0)   # cap at 20x to avoid noise amplification
    return np.clip(audio.astype(np.float32) * gain, -1.0, 1.0)


def pad_audio(audio: np.ndarray, sample_rate: int = 16000, pad_sec: float = 0.25) -> np.ndarray:
    """Prepend and append silence so Whisper doesn't miss the opening syllable."""
    pad = np.zeros(int(pad_sec * sample_rate), dtype=np.float32)
    return np.concatenate([pad, audio.astype(np.float32), pad])


class VAD:
    def __init__(self, threshold: float = 0.008):
        """
        threshold — RMS energy floor for speech detection.
          0.005  very sensitive (catches whispers, more false positives)
          0.008  recommended default
          0.015  old default — missed quiet/distant speech
          0.025  aggressive — only loud close speech
        Set SILERO=1 in .env to use Silero VAD for better accuracy in noisy rooms.
        """
        self._threshold = threshold
        self._engine    = "energy"
        self._model     = None
        if os.getenv("SILERO", "0") != "0":
            self._try_silero()

    def _try_silero(self) -> bool:
        try:
            import torch
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad", force_reload=False, onnx=False, verbose=False,
            )
            self._model = model
            self._engine = "silero"
            print("[VAD] Using Silero VAD")
            return True
        except Exception:
            print("[VAD] Using energy-based VAD (set SILERO=1 for better accuracy)")
            return False

    def is_speech(self, audio: np.ndarray, sample_rate: int = 16000) -> bool:
        if self._engine == "silero":
            try:
                import torch
                tensor = torch.FloatTensor(audio.astype(np.float32))
                return float(self._model(tensor, sample_rate).item()) > 0.5
            except Exception:
                pass
        return float(np.sqrt(np.mean(audio.astype(np.float32) ** 2))) > self._threshold


class SpeechAccumulator:
    """
    Accumulates VAD-classified microphone chunks and emits a ready-to-transcribe
    numpy array when a speech segment is complete.

    Key improvements:
    - Overlap buffer: prepends the last `overlap_sec` of the previous segment
      as context, so words at the start of a new burst are never clipped.
    - Minimum duration: skips clips shorter than `min_speech_sec` to avoid
      Whisper hallucinations on background noise pops.
    - Auto normalize + pad: every emitted segment is RMS-normalised and has
      silence padding added before being passed to Whisper.
    """

    def __init__(
        self,
        sample_rate: int   = 16000,
        silence_sec: float = 1.0,
        max_sec:     float = 30.0,
        overlap_sec: float = 0.5,
        min_speech_sec: float = 0.6,
        pad_sec:     float = 0.25,
    ):
        self._sr             = sample_rate
        self._silence_thresh = int(silence_sec * sample_rate)
        self._max_samples    = int(max_sec     * sample_rate)
        self._overlap_n      = int(overlap_sec * sample_rate)
        self._min_n          = int(min_speech_sec * sample_rate)
        self._pad_sec        = pad_sec

        self._buf:             list[np.ndarray] = []
        self._silence_samples: int  = 0
        self._in_speech:       bool = False
        self._prev_tail:       Optional[np.ndarray] = None   # overlap context

    def add(self, chunk: np.ndarray, is_speech: bool) -> Optional[np.ndarray]:
        """Add one chunk. Returns audio ready for Whisper, or None.

        The max_samples hard-cap now fires in BOTH branches:
        - During speech  → continuous talkers (news anchors, fast speakers) get
          flushed every MAX_SPEECH_SEC even without a pause.
        - During silence → original behaviour, also catches the edge case where
          the buffer crept past the limit on the last speech block.
        Previously the check only lived in the silence branch, so unbroken speech
        (Bloomberg, lectures, rapid conversation) would never hit it and the whole
        recording accumulated into one or two giant chunks.
        """
        if is_speech:
            self._buf.append(chunk)
            self._silence_samples = 0
            self._in_speech = True
            # Hard-cap flush during continuous speech (the critical fix for fast speakers)
            if sum(len(c) for c in self._buf) >= self._max_samples:
                return self._flush()
        elif self._in_speech:
            self._buf.append(chunk)
            self._silence_samples += len(chunk)
            total = sum(len(c) for c in self._buf)
            if self._silence_samples >= self._silence_thresh or total >= self._max_samples:
                return self._flush()
        return None

    def flush(self) -> Optional[np.ndarray]:
        """Force-flush remaining audio at recording stop."""
        return self._flush() if self._in_speech else None

    def _flush(self) -> Optional[np.ndarray]:
        if not self._buf:
            return None

        raw = np.concatenate(self._buf)
        self._buf             = []
        self._silence_samples = 0
        self._in_speech       = False

        # Save tail before minimum-duration check so overlap persists
        new_tail = raw[-self._overlap_n:].copy() if len(raw) >= self._overlap_n else raw.copy()

        # Skip clips that are too short
        if len(raw) < self._min_n:
            self._prev_tail = new_tail
            return None

        # Prepend overlap from previous segment (catches first word of new burst)
        old_tail = self._prev_tail
        self._prev_tail = new_tail

        if old_tail is not None:
            raw = np.concatenate([old_tail, raw])

        # Normalize and pad — the two audio-quality improvements
        raw = normalize_audio(raw)
        raw = pad_audio(raw, self._sr, self._pad_sec)
        return raw
