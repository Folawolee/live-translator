# backend/app/asr.py
from faster_whisper import WhisperModel   # ← this is correct
import numpy as np

_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading faster-whisper model (medium)...")
        _model = WhisperModel(
            "medium",
            device="cpu",
            compute_type="int8"
        )
    return _model

def transcribe_audio(audio_np: np.ndarray) -> str:
    model = get_model()
    try:
        segments, info = model.transcribe(
            audio_np,
            language="en",
            vad_filter=False,
            beam_size=5
        )
        text = " ".join(
            segment.text.strip()
            for segment in segments
            if segment.text and segment.text.strip()
        )
        return text
    except Exception as e:
        print(f"Transcription failed: {e}")
        return ""