# STT service

FastAPI wrapper around a Whisper-family speech-to-text model, exposed as a single-purpose HTTP service on port `8000` (mapped to `8001` externally by `docker-compose`).

## Request flow

`POST /transcribe` takes `{ audio_key }`.

1. Resolve the audio file at `STORAGE_DIR/<audio_key>` (404 if it isn't there). The file is read in place — no copy is made, so it isn't touched or deleted by this service.
2. Run transcription with `word_timestamps=True` enabled, which turns on the model's VAD-based segmentation internally — better boundaries on silence/pauses than a single unsegmented pass.
3. Concatenate segment texts into one string and return `{ text }`. Per-segment/per-word timing is discarded at this layer; only the joined transcript is returned. If callers need word-level timestamps later, that's already computed upstream and just needs threading through the response model.

This is the simplest of the three services — no output files at all, since a transcript is just returned inline as JSON.

## Model lifecycle

Loaded once at startup via `lifespan`, pinned to `cuda`, sized by `WHISPER_MODEL_SIZE` (defaults to `base` — the smallest general-purpose checkpoint, a deliberate speed/accuracy tradeoff for a self-hosted default). `GET /health` reflects load state for readiness probing.

## Auth

Same pattern as the other two services: a single bearer token (`API_KEY`) checked on every route, meant for service-to-service calls from the frontend backend rather than direct end-user auth.

## Storage layout

Audio to transcribe has to already exist under `STORAGE_DIR` (default `./storage`, mounted at `/app/storage` in the container) — `audio_key` is just a relative path into it. Nothing else lives here; this service has no output directory.

## Config (env)

| Var | Purpose |
|---|---|
| `API_KEY` | shared secret for the auth header |
| `WHISPER_MODEL_SIZE` | model checkpoint size (`base` by default — trade up for accuracy, down for latency/VRAM) |
| `STORAGE_DIR` | root directory audio inputs are read from, default `./storage` |

## Deployment

Own Docker image on a CUDA base image, run via `docker-compose` with a GPU reservation and a bind-mounted `./STT/storage` volume. Stateless besides the resident model — horizontally scalable per-GPU.
