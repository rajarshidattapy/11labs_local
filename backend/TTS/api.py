import logging
import os
import uuid
from contextlib import asynccontextmanager

import boto3
import torch
import torchaudio
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from zipvoice.luxvoice import LuxTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ponytail: vocos.return_48k defaults to True (return_smooth=False), which decodes
# at 48kHz. If LuxTTS's default inference mode changes, this must change too.
SAMPLE_RATE = 48000

lux_tts: LuxTTS | None = None
API_KEY = os.getenv("API_KEY")

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
S3_PREFIX = os.getenv("S3_PREFIX", "tts-outputs")
S3_BUCKET = os.getenv("S3_BUCKET", "elevenlabs-clone")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global lux_tts
    logger.info("Loading LuxTTS model...")
    lux_tts = LuxTTS(device="cuda")
    logger.info("LuxTTS model loaded successfully")
    yield
    logger.info("Shutting down TTS API")


app = FastAPI(title="TTS API", lifespan=lifespan)


class GenerateRequest(BaseModel):
    text: str
    prompt_audio_s3_key: str
    num_steps: int = 4
    guidance_scale: float = 3.0
    t_shift: float = 0.5
    speed: float = 1.0


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_speech(request: GenerateRequest):
    if not lux_tts:
        raise HTTPException(status_code=500, detail="Model not loaded")

    prompt_path = f"/tmp/{uuid.uuid4()}.wav"
    output_filename = f"{uuid.uuid4()}.wav"
    local_path = f"/tmp/{output_filename}"

    try:
        s3_client.download_file(S3_BUCKET, request.prompt_audio_s3_key, prompt_path)

        encode_dict = lux_tts.encode_prompt(prompt_path)
        wav = lux_tts.generate_speech(
            request.text,
            encode_dict,
            num_steps=request.num_steps,
            guidance_scale=request.guidance_scale,
            t_shift=request.t_shift,
            speed=request.speed,
        )

        torchaudio.save(local_path, wav if wav.ndim == 2 else wav.unsqueeze(0), sample_rate=SAMPLE_RATE)

        s3_key = f"{S3_PREFIX}/{output_filename}"
        s3_client.upload_file(local_path, S3_BUCKET, s3_key)
        presigned_url = s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600
        )

        return {"audio_url": presigned_url, "s3_key": s3_key}
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail="Error generating speech")
    finally:
        for path in (prompt_path, local_path):
            if os.path.exists(path):
                os.remove(path)


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if lux_tts:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
