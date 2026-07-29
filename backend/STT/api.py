import logging
import os
from contextlib import asynccontextmanager

from faster_whisper import WhisperModel
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model: WhisperModel | None = None
API_KEY = os.getenv("API_KEY")
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="API key is missing")
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    logger.info(f"Loading faster-whisper model ({MODEL_SIZE})...")
    model = WhisperModel(MODEL_SIZE, device="cuda")
    logger.info("faster-whisper model loaded successfully")
    yield
    logger.info("Shutting down STT API")


app = FastAPI(title="STT API", lifespan=lifespan)


class TranscribeRequest(BaseModel):
    audio_key: str


@app.post("/transcribe", dependencies=[Depends(verify_api_key)])
async def transcribe(request: TranscribeRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")

    audio_path = os.path.join(STORAGE_DIR, request.audio_key)
    if not os.path.isfile(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    try:
        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        text = "".join(segment.text for segment in segments).strip()
        return {"text": text}
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail="Error transcribing audio")


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if model:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
