# backend/app/asr.py
from faster_whisper import WhisperModel
import numpy as np
import logging

logger = logging.getLogger(__name__)

_model = None

def get_model():
    global _model
    if _model is None:
        logger.info("Loading faster-whisper model (medium)...")
        _model = WhisperModel(
            "medium",
            device="cpu",
            compute_type="int8"
        )
    return _model

def transcribe_audio(audio_np: np.ndarray, language: str = "en") -> str:
    model = get_model()
    try:
        segments, info = model.transcribe(
            audio_np,
            language=language,
            vad_filter=False,
            beam_size=1,
            without_timestamps=True
        )
        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text and segment.text.strip()
        )
        logger.info(f"Raw transcription result: '{text}'")
        return text
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""