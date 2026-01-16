# backend/app/main.py
import os
import asyncio
import logging
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
import numpy as np
from queue import Queue
from contextlib import asynccontextmanager

# Relative import – files are in the same folder
from .asr import transcribe_audio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration (use environment variables in production)
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    logger.info("Starting Live Translator backend...")
    yield
    logger.info("Shutting down Live Translator backend...")

app = FastAPI(
    title="Live Nigerian Language Translator – MVP",
    description="Real-time speech-to-text translation backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
audio_queue: Queue = Queue()
active_connections: List[WebSocket] = []

@app.get("/", response_class=HTMLResponse)
async def root():
    """Simple welcome page"""
    return """
    <html>
        <head><title>Live Translator MVP</title></head>
        <body style="font-family: system-ui; max-width: 800px; margin: 40px auto; text-align: center;">
            <h1>Live Nigerian Language Translator</h1>
            <p><strong>Backend is running</strong></p>
            <p>WebSocket endpoint: <code>ws://localhost:8000/ws</code></p>
            <p>Interactive API documentation: 
                <a href="/docs">Swagger UI</a> | 
                <a href="/redoc">ReDoc</a>
            </p>
            <p style="margin-top: 2rem; color: #666;">
                Connect a client to /ws to start real-time transcription.
            </p>
        </body>
    </html>
    """


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "active_connections": len(active_connections),
        "queue_size": audio_queue.qsize()
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for audio streaming"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"Client connected. Total active: {len(active_connections)}")

    try:
        while True:
            data = await websocket.receive_bytes()
            try:
                chunk = np.frombuffer(data, dtype=np.float32)
                audio_queue.put_nowait(chunk)  # non-blocking put
            except ValueError as e:
                logger.warning(f"Invalid audio chunk: {e}")
            except Queue.Full:
                logger.warning("Audio queue full - dropping chunk")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total active: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            active_connections.remove(websocket)
        except ValueError:
            pass


async def audio_processor():
    """Background task: processes queued audio in batches"""
    buffer: List[np.ndarray] = []
    while True:
        try:
            if not audio_queue.empty():
                while not audio_queue.empty():
                    buffer.append(audio_queue.get_nowait())

                if len(buffer) >= 5:  # ~0.5–1s of audio depending on chunk size
                    try:
                        audio_np = np.concatenate(buffer)
                        text = await asyncio.to_thread(transcribe_audio, audio_np)

                        if text and text.strip():
                            subtitle = f"→ {text.capitalize()}."
                            logger.info(f"Transcribed: {subtitle[:80]}...")

                            # Send to all connected clients
                            dead_connections = []
                            for ws in active_connections:
                                try:
                                    await ws.send_text(subtitle)
                                except Exception:
                                    dead_connections.append(ws)

                            for ws in dead_connections:
                                active_connections.remove(ws)
                                logger.debug("Removed dead connection")

                    except Exception as e:
                        logger.error(f"Transcription error: {e}")
                    finally:
                        buffer.clear()  # always reset

            await asyncio.sleep(0.12)  # ~8–10 checks per second

        except Exception as e:
            logger.error(f"Processor loop error: {e}")
            await asyncio.sleep(1)  # backoff on error


@app.on_event("startup")
async def startup():
    logger.info("Starting audio processing background task...")
    asyncio.create_task(audio_processor())


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
        workers=1,              # keep at 1 for development
        timeout_keep_alive=30,  # helps with long-lived WS connections
    )