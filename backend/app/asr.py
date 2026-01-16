import numpy as np
import whisper

# Load model once (VERY important)
_model = None

def get_model():
    global _model
    if _model is None:
        print("Loading Whisper model...")
        _model = whisper.load_model("base")  # start small
    return _model


def transcribe_audio(audio_np: np.ndarray) -> str:
    """
    audio_np: float32 numpy array, mono, 16kHz
    """
    if audio_np is None or len(audio_np) == 0:
        return ""

    model = get_model()

    # Whisper expects float32 numpy array
    result = model.transcribe(
        audio_np,
        language="en",       # later change / auto-detect
        fp16=False
    )

    return result.get("text", "").strip()
