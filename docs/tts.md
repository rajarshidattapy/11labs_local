# TTS service

FastAPI wrapper around a flow-matching text-to-speech model, exposed as a single-purpose HTTP service on port `8000`.

## Request flow

`POST /generate` takes `{ text, prompt_audio_key, num_steps, guidance_scale, t_shift, speed }`.

1. Resolve the reference clip at `STORAGE_DIR/<prompt_audio_key>`. The model is voice-cloning, not preset-voice — every request needs a real audio sample of the target voice, so the file has to already exist on disk (404 if it doesn't).
2. Encode the reference clip into the model's conditioning representation (`encode_prompt`).
3. Run generation against the requested text using that conditioning plus the tunable sampling params (`num_steps`, `guidance_scale`, `t_shift`, `speed`).
4. Write the output waveform straight to `STORAGE_DIR/tts-outputs/<uuid>.wav` and return `{ audio_url, file_key }`, where `audio_url` is that file served back through the app's own static file mount.

Everything the service produces stays on the same disk it runs on — no upload step, no external storage credentials.

Sample rate is fixed at 48kHz to match the vocoder's default decode mode (see the `ponytail:` comment in `api.py` — if the model's default inference mode changes, this constant has to move with it).

## Model lifecycle

The model loads once at process startup via FastAPI's `lifespan` context manager, pinned to `cuda`, and stays resident for the life of the process — no per-request load/unload. `GET /health` reports whether the model finished loading, which is what the container orchestration should poll before routing traffic to it.

## Auth

Every route except none — both `/generate` and `/health` — requires a bearer token in the `Authorization` header, checked against a single shared `API_KEY` env var. This is service-to-service auth (the frontend backend calls it, not end users), so it's intentionally a static shared secret rather than per-user tokens.

## Storage layout

Everything lives under `STORAGE_DIR` (default `./storage`, mounted at `/app/storage` in the container):

- `voice-prompts/` — reference clips you drop in yourself; `prompt_audio_key` is a path relative to this root (e.g. `voice-prompts/andreas.wav`)
- `tts-outputs/` — generated clips, created on demand

`GET /files/<key>` (a static file mount over the whole `STORAGE_DIR`) serves both — it's how `audio_url` in the response is actually reachable.

## Config (env)

| Var | Purpose |
|---|---|
| `API_KEY` | shared secret for the auth header |
| `STORAGE_DIR` | root directory for prompts and outputs, default `./storage` |
| `PUBLIC_BASE_URL` | host-facing base URL used to build `audio_url` in responses, default `http://localhost:8000` |

## Deployment

Built as its own Docker image (`Dockerfile.api`) on a CUDA-enabled PyTorch base, run via `docker-compose` with an NVIDIA GPU reservation and a bind-mounted `./TTS/storage` volume (that's where you drop reference clips from the host, and where outputs persist across restarts). Stateless aside from the loaded model weights and the storage volume — safe to restart or scale horizontally as long as each replica gets a GPU and access to the storage dir.
