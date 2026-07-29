# TTS service

FastAPI wrapper around a flow-matching text-to-speech model, exposed as a single-purpose HTTP service on port `8000`.

## Request flow

`POST /generate` takes `{ text, prompt_audio_s3_key, num_steps, guidance_scale, t_shift, speed }`.

1. Download the reference clip from S3 (`prompt_audio_s3_key`) to a scratch file. The model is voice-cloning, not preset-voice — every request needs a real audio sample of the target voice.
2. Encode the reference clip into the model's conditioning representation (`encode_prompt`).
3. Run generation against the requested text using that conditioning plus the tunable sampling params (`num_steps`, `guidance_scale`, `t_shift`, `speed`).
4. Write the output waveform to a scratch `.wav`, upload it to S3, return a presigned URL (1h expiry) and the S3 key.
5. Scratch files (`/tmp/*.wav`) are deleted in a `finally` block regardless of success/failure — nothing generated is kept on local disk.

Sample rate is fixed at 48kHz to match the vocoder's default decode mode (see the `ponytail:` comment in `api.py` — if the model's default inference mode changes, this constant has to move with it).

## Model lifecycle

The model loads once at process startup via FastAPI's `lifespan` context manager, pinned to `cuda`, and stays resident for the life of the process — no per-request load/unload. `GET /health` reports whether the model finished loading, which is what the container orchestration should poll before routing traffic to it.

## Auth

Every route except none — both `/generate` and `/health` — requires a bearer token in the `Authorization` header, checked against a single shared `API_KEY` env var. This is service-to-service auth (the frontend backend calls it, not end users), so it's intentionally a static shared secret rather than per-user tokens.

## Config (env)

| Var | Purpose |
|---|---|
| `API_KEY` | shared secret for the auth header |
| `S3_BUCKET` | bucket outputs are uploaded to (and prompt clips read from) |
| `S3_PREFIX` | key prefix for generated output, default `tts-outputs` |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials; if the access-key vars are unset, boto3 falls back to the ambient AWS credential chain (instance role, etc.) |

## Deployment

Built as its own Docker image (`Dockerfile.api`) on a CUDA-enabled PyTorch base, run via `docker-compose` with an NVIDIA GPU reservation. Stateless aside from the loaded model weights — safe to restart or scale horizontally as long as each replica gets a GPU.
