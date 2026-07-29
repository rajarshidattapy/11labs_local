import logging
import os
import uuid
from contextlib import asynccontextmanager

import torch
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gen_wav import SAMPLE_RATE, gen_wav, initialize_model
from vocoder.bigvgan.models import VocoderBigVGAN
import soundfile as sf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables
sampler = None
vocoder = None
API_KEY = os.getenv("API_KEY")
device = 'cuda' if torch.cuda.is_available() else 'cpu'

STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
OUTPUTS_DIR = os.path.join(STORAGE_DIR, "make-an-audio-outputs")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8002")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def verify_api_key(authorization: str = Header(None)):
    if not authorization:
        logger.warning("No API key provided")
        raise HTTPException(status_code=401, detail="API key is missing")

    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    else:
        token = authorization

    if token != API_KEY:
        logger.warning("Invalid API key provided")
        raise HTTPException(status_code=401, detail="Invalid API key")

    return token


@asynccontextmanager
async def lifespan(app: FastAPI):
    global sampler, vocoder
    logger.info("Loading Make-an-Audio model...")
    try:
        sampler = initialize_model(
            'configs/text_to_audio/txt2audio_args.yaml', 'useful_ckpts/maa1_full.ckpt')
        vocoder = VocoderBigVGAN('useful_ckpts/bigvgan', device=device)

        logger.info("Make-an-Audio model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    yield

    logger.info("Shutting down Make-an-Audio API")

app = FastAPI(title="Make-an-Audio API",
              lifespan=lifespan)
app.mount("/files", StaticFiles(directory=STORAGE_DIR), name="files")


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate", dependencies=[Depends(verify_api_key)])
async def generate_speech(request: GenerateRequest):
    if not sampler or not vocoder:
        raise HTTPException(status_code=500, detail="Models not loaded")

    try:
        wav_list = gen_wav(sampler, vocoder, prompt=request.prompt, ddim_steps=100,
                           scale=3.0, duration=10, n_samples=1)

        audio = wav_list[0]

        output_key = f"make-an-audio-outputs/{uuid.uuid4()}.wav"
        output_path = os.path.join(STORAGE_DIR, output_key)

        sf.write(output_path, audio, samplerate=SAMPLE_RATE)

        return {
            "audio_url": f"{PUBLIC_BASE_URL}/files/{output_key}",
            "file_key": output_key,
        }
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        raise HTTPException(
            status_code=500, detail="Error generating audio")


@app.get("/health", dependencies=[Depends(verify_api_key)])
async def health_check():
    if vocoder and sampler:
        return {"status": "healthy", "model": "loaded"}
    return {"status": "unhealthy", "model": "not loaded"}
