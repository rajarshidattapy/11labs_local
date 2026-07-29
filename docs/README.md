# 11labs-local

Self-hosted ElevenLabs-style audio AI suite: text-to-speech, voice conversion, and text-to-sound-effects, running on your own GPU instead of a paid API.

## Features

- **Text-to-Speech** — generate speech from text with StyleTTS2, choose from preset voices
- **Speech-to-Speech** — upload a clip and convert it to a target voice with Seed-VC
- **Sound Effects** — generate sound effects from a text prompt (Make-An-Audio)
- **History** — past generations per user, saved to your own database
- Auth via Clerk, background jobs via Inngest, generation runs async and polls for completion

## Stack

- `frontend/` — Next.js 15 (App Router) + Prisma/SQLite + Clerk + Inngest
- `backend/` — three GPU inference services (TTS, STT, sound_generator), each a FastAPI app in its own Docker image

## Setup

### 1. Backend (GPU inference services)

Requires an NVIDIA GPU + Docker with the NVIDIA Container Toolkit.

```bash
cd backend
docker compose up --build
```

This starts:
- TTS API on `:8000`
- STT on `:8001`
- Sound generator API on `:8002`

No GPU handy? Skip this — the frontend has a built-in mock API (`/api/mock/*`) that stands in for these services so you can run the UI end-to-end without them.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # fill in Clerk keys at minimum
npx prisma db push
npm run dev
```

Open `http://localhost:3000`.

Required env vars (see `.env.example`):
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY` — from [dashboard.clerk.com](https://dashboard.clerk.com)
- `DATABASE_URL` — defaults to a local SQLite file, no setup needed
- `TTS_API_ROUTE`, `SOUND_GENERATOR_API_ROUTE`, `BACKEND_API_KEY` — point these at the backend services above, or leave the defaults to hit the mock API

### 3. Background jobs (optional, for real generation)

Generation requests are dispatched through Inngest. For local dev:

```bash
npm run inngest-dev
```
