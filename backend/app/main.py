# backend/app/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
from queue import Queue
import asyncio

# Use relative import (recommended when files are in the same directory)
from .asr import transcribe_audio, get_model

app = FastAPI(title="Live Nigerian Language Translator MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

audio_queue = Queue()
active_connections = []  # simple broadcast for MVP (single speaker)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_bytes()
            # Assuming browser sends float32 mono PCM
            chunk = np.frombuffer(data, dtype=np.float32)
            audio_queue.put(chunk)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        active_connections.remove(websocket)


async def audio_processor():
    buffer = []
    while True:
        if not audio_queue.empty():
            while not audio_queue.empty():
                buffer.append(audio_queue.get())

            if len(buffer) >= 5:  # ≈ 0.5–1 second of audio (adjust based on chunk size)
                try:
                    audio_np = np.concatenate(buffer)
                    text = transcribe_audio(audio_np)
                    
                    if text and text.strip():
                        subtitle = f"→ {text.capitalize()}."
                        # Broadcast to all connected clients
                        for ws in list(active_connections):
                            try:
                                await ws.send_text(subtitle)
                            except:
                                pass  # ignore failed sends
                except Exception as e:
                    print(f"Transcription error: {e}")
                finally:
                    buffer = []  # always clear buffer

        await asyncio.sleep(0.1)  # faster polling than 0.2s for better responsiveness


@app.on_event("startup")
async def startup_event():
    print("Starting audio processor...")
    asyncio.create_task(audio_processor())


if __name__ == "__main__":
    import uvicorn
    # Recommended: run from backend/ folder with:
    # python -m uvicorn app.main:app --reload --port 8000
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )