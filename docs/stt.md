# STT service

FastAPI wrapper around a Whisper-family speech-to-text model, exposed as a single-purpose HTTP service on port `8000` (mapped to `8001` externally by `docker-compose`).

## Request flow

`POST /transcribe` takes `{ audio_s3_key }`.

1. Download the audio file from S3 to a scratch path (no extension — the model's audio loader sniffs format from content, not filename).
2. Run transcription with `word_timestamps=True` enabled, which turns on the model's VAD-based segmentation internally — better boundaries on silence/pauses than a single unsegmented pass.
3. Concatenate segment texts into one string and return `{ text }`. Per-segment/per-word timing is discarded at this layer; only the joined transcript is returned. If callers need word-level timestamps later, that's already computed upstream and just needs threading through the response model.
4. The scratch file is deleted in a `finally` block regardless of outcome.

This is the simplest of the three services — no S3 upload on the output side, since a transcript is just returned inline as JSON rather than stored as a blob.

## Model lifecycle

Loaded once at startup via `lifespan`, pinned to `cuda`, sized by `WHISPER_MODEL_SIZE` (defaults to `base` — the smallest general-purpose checkpoint, a deliberate speed/accuracy tradeoff for a self-hosted default). `GET /health` reflects load state for readiness probing.

## Auth

Same pattern as the other two services: a single bearer token (`API_KEY`) checked on every route, meant for service-to-service calls from the frontend backend rather than direct end-user auth.

## Config (env)

| Var | Purpose |
|---|---|
| `API_KEY` | shared secret for the auth header |
| `WHISPER_MODEL_SIZE` | model checkpoint size (`base` by default — trade up for accuracy, down for latency/VRAM) |
| `S3_BUCKET` | bucket audio inputs are read from |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials; falls back to the ambient AWS credential chain if the key vars are unset |

## Deployment

Own Docker image on a CUDA base image, run via `docker-compose` with a GPU reservation. Stateless besides the resident model — horizontally scalable per-GPU.
