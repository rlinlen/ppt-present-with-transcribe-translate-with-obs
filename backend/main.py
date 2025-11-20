from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from audio_capture import AudioCapture
from transcribe_client import TranscribeClient

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

@app.get("/")
async def root():
    return FileResponse(str(frontend_path / "subtitles.html"))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    audio_capture = AudioCapture()
    transcribe_client = TranscribeClient()
    audio_queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    is_connected = True
    
    async def transcribe_callback(result):
        if is_connected:
            try:
                await websocket.send_json(result)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
    
    async def process_audio():
        try:
            await transcribe_client.start_stream(transcribe_callback)
        except Exception as e:
            logger.error(f"Transcribe error: {e}")
    
    async def send_audio_to_transcribe():
        while is_connected:
            try:
                audio_chunk = await audio_queue.get()
                await transcribe_client.send_audio(audio_chunk)
            except Exception as e:
                logger.error(f"Error sending audio: {e}")
                break
    
    def audio_callback(audio_data):
        if is_connected:
            try:
                asyncio.run_coroutine_threadsafe(audio_queue.put(audio_data), loop)
            except Exception as e:
                logger.error(f"Error queuing audio: {e}")
    
    try:
        audio_capture.start(audio_callback)
        
        await asyncio.gather(
            process_audio(),
            send_audio_to_transcribe()
        )
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        is_connected = False
        audio_capture.stop()
        await transcribe_client.stop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
