# backend/app/main.py
import os
import asyncio
import logging
import json
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import numpy as np
from queue import Queue
from contextlib import asynccontextmanager

from .asr import transcribe_audio, get_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

# Store audio chunks with their associated websocket and language
class AudioTask:
    def __init__(self, ws: WebSocket, chunks: List[np.ndarray], language: str):
        self.ws = ws
        self.chunks = chunks
        self.language = language

audio_queue: Queue = Queue()
active_connections: dict[WebSocket, dict] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Live Translator backend...")
    # Pre-load the model on startup
    logger.info("Pre-loading Whisper model...")
    await asyncio.to_thread(get_model)
    logger.info("Model loaded successfully!")
    
    # Start audio processor
    asyncio.create_task(audio_processor())
    
    yield
    logger.info("Shutting down Live Translator backend...")

app = FastAPI(
    title="Live Nigerian Language Translator",
    description="Real-time speech-to-text translation backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head><title>Live Translator</title></head>
        <body style="font-family: system-ui; max-width: 800px; margin: 40px auto; text-align: center;">
            <h1>🎙️ Live Nigerian Language Translator</h1>
            <p><strong>Backend is running</strong></p>
            <p>WebSocket: <code>ws://localhost:8000/ws</code></p>
            <p><a href="/docs">API Docs</a></p>
        </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_connections": len(active_connections),
        "queue_size": audio_queue.qsize()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Initialize connection state
    active_connections[websocket] = {
        "language": "en",
        "buffer": []
    }
    
    logger.info(f"Client connected. Total: {len(active_connections)}")

    try:
        while True:
            message = await websocket.receive()

            # Handle text messages (language changes)
            if "text" in message:
                try:
                    msg = json.loads(message["text"])
                    if msg.get("type") == "set_language":
                        language = msg.get("language", "en")
                        active_connections[websocket]["language"] = language
                        logger.info(f"Language set to: {language}")
                        await websocket.send_json({
                            "type": "status",
                            "message": f"Language set to {language}"
                        })
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received")

            # Handle binary messages (audio data)
            elif "bytes" in message:
                data = message["bytes"]
                try:
                    chunk = np.frombuffer(data, dtype=np.float32)
                    active_connections[websocket]["buffer"].append(chunk)
                    
                    # Queue for processing when buffer is large enough
                    if len(active_connections[websocket]["buffer"]) >= 5:
                        chunks = active_connections[websocket]["buffer"].copy()
                        language = active_connections[websocket]["language"]
                        active_connections[websocket]["buffer"].clear()
                        
                        logger.info(f"Queueing {len(chunks)} chunks for transcription")
                        audio_queue.put_nowait(
                            AudioTask(websocket, chunks, language)
                        )
                        
                        # Send processing notification
                        await websocket.send_json({
                            "type": "status",
                            "message": "Processing audio..."
                        })
                        
                except ValueError as e:
                    logger.warning(f"Invalid audio chunk: {e}")

    except WebSocketDisconnect:
        if websocket in active_connections:
            del active_connections[websocket]
        logger.info(f"Client disconnected. Total: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            del active_connections[websocket]

async def audio_processor():
    """Background task to process queued audio"""
    logger.info("Audio processor started")
    
    while True:
        if not audio_queue.empty():
            task: AudioTask = audio_queue.get_nowait()
            
            try:
                # Combine audio chunks
                audio_np = np.concatenate(task.chunks)
                logger.info(f"Processing {len(audio_np)} audio samples ({len(audio_np)/16000:.2f} seconds)")
                
                # Transcribe
                text = await asyncio.to_thread(
                    transcribe_audio, 
                    audio_np, 
                    task.language
                )
                
                if text and text.strip():
                    logger.info(f"✓ Transcribed ({task.language}): '{text}'")
                    
                    # Send back to the specific client
                    try:
                        if task.ws in active_connections:
                            response = {
                                "type": "transcription",
                                "text": text.strip(),
                                "language": task.language
                            }
                            await task.ws.send_json(response)
                            logger.info("✓ Transcription sent to client")
                        else:
                            logger.warning("⚠ WebSocket no longer active, cannot send transcription")
                    except Exception as e:
                        logger.error(f"✗ Failed to send transcription: {e}")
                else:
                    logger.info("No speech detected in audio chunk")
                        
            except Exception as e:
                logger.error(f"Transcription error: {e}", exc_info=True)
        
        await asyncio.sleep(0.05)  # Check more frequently

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {HOST}:{PORT}")
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info",
    )