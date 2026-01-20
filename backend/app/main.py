# backend/app/main.py

import os
import json
import asyncio
import logging
import numpy as np
from typing import Dict, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .asr import transcribe_audio, get_model

# -------------------------------------------------------------------
# Logging
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

SAMPLE_RATE = 16000
CHUNKS_PER_BATCH = 5  # how many audio chunks before transcription

# -------------------------------------------------------------------
# Connection State
# -------------------------------------------------------------------

class ConnectionState:
    def __init__(self):
        self.language: str = "en"
        self.buffer: List[np.ndarray] = []

active_connections: Dict[WebSocket, ConnectionState] = {}
audio_queue: asyncio.Queue = asyncio.Queue()

# -------------------------------------------------------------------
# App Lifespan
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting backend...")
    logger.info("Loading Whisper model...")
    await asyncio.to_thread(get_model)
    logger.info("Whisper model loaded")

    asyncio.create_task(audio_processor())
    yield

    logger.info("Shutting down backend...")

# -------------------------------------------------------------------
# FastAPI App
# -------------------------------------------------------------------

app = FastAPI(
    title="Live Speech Transcription Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <h2>Live Transcription Backend</h2>
    <p>Status: running</p>
    <p>WebSocket: ws://localhost:8000/ws</p>
    """

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "connections": len(active_connections),
        "queue": audio_queue.qsize(),
    }

# -------------------------------------------------------------------
# WebSocket Endpoint
# -------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections[websocket] = ConnectionState()

    logger.info(f"Client connected ({len(active_connections)})")

    try:
        while True:
            message = await websocket.receive()

            # -------------------------
            # Text messages (JSON)
            # -------------------------
            if "text" in message:
                try:
                    data = json.loads(message["text"])
                    if data.get("type") == "set_language":
                        lang = data.get("language", "en")
                        active_connections[websocket].language = lang

                        await websocket.send_json({
                            "type": "status",
                            "message": f"Language set to {lang}"
                        })

                        logger.info(f"Language updated → {lang}")

                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received")

            # -------------------------
            # Binary audio data
            # -------------------------
            elif "bytes" in message:
                audio_bytes = message["bytes"]

                try:
                    audio_chunk = np.frombuffer(audio_bytes, dtype=np.float32)
                except ValueError:
                    logger.warning("Invalid audio buffer")
                    continue

                state = active_connections.get(websocket)
                if not state:
                    continue

                state.buffer.append(audio_chunk)

                if len(state.buffer) >= CHUNKS_PER_BATCH:
                    chunks = state.buffer.copy()
                    state.buffer.clear()

                    await audio_queue.put((
                        websocket,
                        chunks,
                        state.language
                    ))

                    await websocket.send_json({
                        "type": "status",
                        "message": "Processing audio..."
                    })

    except WebSocketDisconnect:
        logger.info("Client disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

    finally:
        active_connections.pop(websocket, None)
        logger.info(f"Active connections: {len(active_connections)}")

# -------------------------------------------------------------------
# Background Audio Processor
# -------------------------------------------------------------------

async def audio_processor():
    logger.info("Audio processor started")

    while True:
        websocket, chunks, language = await audio_queue.get()

        try:
            audio_np = np.concatenate(chunks)

            duration = len(audio_np) / SAMPLE_RATE
            logger.info(f"Transcribing {duration:.2f}s ({language})")

            text = await asyncio.to_thread(
                transcribe_audio,
                audio_np,
                language
            )

            if text.strip():
                if websocket in active_connections:
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text.strip(),
                        "language": language
                    })
                    logger.info("Transcription sent")

        except Exception as e:
            logger.error(f"Transcription failed: {e}", exc_info=True)

        await asyncio.sleep(0.01)

# -------------------------------------------------------------------
# Run
# -------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )
