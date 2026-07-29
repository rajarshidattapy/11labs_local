# Sound generator service

FastAPI wrapper around a latent-diffusion text-to-audio model plus a BigVGAN-style vocoder, exposed as a single-purpose HTTP service on port `8000` (mapped to `8002` externally).

## Request flow

`POST /generate` takes `{ prompt }` — a free-text description of the sound to generate (e.g. "a bird chirps").

1. `gen_wav` builds a latent noise tensor sized from a fixed duration (10s, hardcoded at the call site — not yet exposed as a request param) via `dur_to_size`, which maps seconds to the model's latent width and rounds up to a multiple of 4 to satisfy the architecture's stride constraints.
2. Text conditioning is computed for the prompt, plus an empty-string conditioning for classifier-free guidance (`scale=3.0` — how strongly generation follows the prompt vs. the unconditional distribution).
3. DDIM sampling runs for a fixed 100 steps, decoding the diffusion output through the first-stage decoder into a spectrogram-like latent, then through the BigVGAN vocoder into a waveform.
4. Output is short-padded with zeros if the vocoded waveform comes back shorter than the requested duration, then written to a scratch `.wav`, uploaded to S3, and returned as a presigned URL + key.
5. Local cleanup happens via a FastAPI `BackgroundTask` (`os.remove`) rather than a `finally` block — the response is sent before cleanup runs, unlike the other two services.

Sample rate is fixed at 16kHz — lower than the TTS service's 48kHz, since this model targets general sound effects rather than speech fidelity.

## Model lifecycle

Two components load at startup under `lifespan`: the diffusion sampler (`initialize_model`, built from a YAML config + checkpoint) and the vocoder, loaded separately from its own checkpoint. Both must load successfully or the app fails startup rather than serving with a partial model. `GET /health` checks both are present.

## Auth

Same shared-bearer-token pattern as the other two services (`API_KEY` header check), for service-to-service calls only.

## Config (env)

| Var | Purpose |
|---|---|
| `API_KEY` | shared secret for the auth header |
| `S3_BUCKET` | bucket outputs are uploaded to |
| `S3_PREFIX` | key prefix for generated output, default `make-an-audio-outputs` |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | S3 credentials; falls back to the ambient AWS credential chain if the key vars are unset |

Sampling params (`ddim_steps`, `scale`, `duration`, `n_samples`) are currently hardcoded in the `/generate` handler rather than request fields — the only tunable input is the prompt text.

## Deployment

Own Docker image on a CUDA-enabled PyTorch base; the image bundles the model configs, weights (`useful_ckpts/`), and vocoder code directly rather than pulling them at runtime, so the built image is self-contained but large. Run via `docker-compose` with a GPU reservation, stateless besides the resident models.
