import logging
import os
import uuid
from contextlib import asynccontextmanager

import boto3
from faster_whisper import WhisperModel
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model: WhisperModel | None = None
API_KEY = os.getenv("API_KEY")
MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="API key is missing")
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    if token != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token


def get_s3_client():
    client_kwargs = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        client_kwargs.update({
            "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
            "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        })
    return boto3.client("s3", **client_kwargs)


s3_client = get_s3_client()
S3_BUCKET = os.getenv("S3_BUCKET", "elevenlabs-clone")


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
    audio_s3_key: str


@app.post("/transcribe", dependencies=[Depends(verify_api_key)])
async def transcribe(request: TranscribeRequest):
    if not model:
        raise HTTPException(status_code=500, detail="Model not loaded")

    local_path = f"/tmp/{uuid.uuid4()}"

    try:
        s3_client.download_file(S3_BUCKET, request.audio_s3_key, local_path)
        segments, _ = model.transcribe(local_path, word_timestamps=True)
        text = "".join(segment.text for segment in segments).strip()
        return {"text": text}
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        raise HTTPException(status_code=500, detail="Error transcribing audio")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if model:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
