import logging
import os
import uuid
from contextlib import asynccontextmanager

import torch
import torchaudio
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from zipvoice.luxvoice import LuxTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ponytail: vocos.return_48k defaults to True (return_smooth=False), which decodes
# at 48kHz. If LuxTTS's default inference mode changes, this must change too.
SAMPLE_RATE = 48000

lux_tts: LuxTTS | None = None
API_KEY = os.getenv("API_KEY")

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
PROMPTS_DIR = os.path.join(STORAGE_DIR, "voice-prompts")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "tts-outputs")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
os.makedirs(PROMPTS_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

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
    global lux_tts
    logger.info("Loading LuxTTS model...")
    lux_tts = LuxTTS(device="cuda")
    logger.info("LuxTTS model loaded successfully")
    yield
    logger.info("Shutting down TTS API")


app = FastAPI(title="TTS API", lifespan=lifespan)
app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")


class GenerateRequest(BaseModel):
    text: str
    prompt_audio_key: str
    num_steps: int = 4
    guidance_scale: float = 3.0
    t_shift: float = 0.5
    speed: float = 1.0


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_speech(request: GenerateRequest):
    if not lux_tts:
        raise HTTPException(status_code=500, detail="Model not loaded")

    prompt_path = os.path.join(STORAGE_DIR, request.prompt_audio_key)
    if not os.path.isfile(prompt_path):
        raise HTTPException(status_code=404, detail="Reference audio not found")

    output_key = f"tts-outputs/{uuid.uuid4()}.wav"
    output_path = os.path.join(STORAGE_DIR, output_key)

    try:
        encode_dict = lux_tts.encode_prompt(prompt_path)
        wav = lux_tts.generate_speech(
            request.text,
            encode_dict,
            num_steps=request.num_steps,
            guidance_scale=request.guidance_scale,
            t_shift=request.t_shift,
            speed=request.speed,
        )

        torchaudio.save(output_path, wav if wav.ndim == 2 else wav.unsqueeze(0), sample_rate=SAMPLE_RATE)

        return {"audio_url": f"{PUBLIC_BASE_URL}/files/{output_key}", "file_key": output_key}
    except Exception as e:
        logger.error(f"Error generating speech: {e}")
        raise HTTPException(status_code=500, detail="Error generating speech")


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if lux_tts:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
