# ViralCraft

AI-powered short video **structure transfer** engine.

ViralCraft learns reusable creative structure from example short videos and applies that structure to new topics, products, or briefs. Every generated video flows through a structured **storyboard JSON** before rendering — no free-form text-to-video shortcuts. The renderer **reuses your uploaded footage** as the visual layer and adds generated captions, structure, and motion graphics on top.

```
user request + retrieved structure cards
  → storyboard JSON
  → Remotion composition (source video / frames as background)
  → rendered mp4
```

> **MVP scope.** This is structure transfer + media remixing, **not** pixel-level VFX editing. The renderer does not perform face filters, object insertion, makeup transfer, inpainting, or true before/after VFX. See [docs/demo_script.md](docs/demo_script.md) for the full scope statement and recommended demo prompts.

---

## Repository Layout

```
apps/
  web/        # Next.js + TypeScript + Tailwind frontend
  api/        # FastAPI backend (upload, analyze, structure card, storyboard, render)
  renderer/   # Remotion video renderer

packages/
  schemas/    # Shared TypeScript schema definitions
  prompts/    # LLM prompt templates

data/
  uploads/         # Source uploads (gitignored)
  frames/          # Extracted frames (gitignored)
  renders/         # Rendered mp4 outputs + media_assets.json sidecars (gitignored)
  knowledge_base/  # Structure cards + storyboards (gitignored)

docs/
  architecture.md
  structure_schema.md
  demo_script.md   # 3-minute live demo script + recommended prompts
```

---

## Prerequisites

- **Node.js** ≥ 20
- **npm** ≥ 10 (workspace support)
- **Python** ≥ 3.11
- **FFmpeg** on PATH (`brew install ffmpeg` on macOS, optional but useful for inspecting outputs)

---

## First-time setup

```bash
# 1. Install all JS workspaces (web, renderer, schemas)
npm install

# 2. Set up the Python API
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ../..

# 3. Copy env templates
cp apps/web/.env.example apps/web/.env.local
cp apps/api/.env.example apps/api/.env

# 4. (Optional) Set up real Seed credentials in apps/api/.env.
#    Otherwise the API runs in mock mode — see apps/api/README.md.
```

The first `npm install --workspace apps/renderer` will also download a ~140 MB Chromium for Remotion; subsequent runs reuse it.

---

## Running locally

Open three terminals.

### Frontend (Next.js)

```bash
npm run dev --workspace apps/web
# → http://localhost:3000
```

### Backend (FastAPI)

```bash
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health
# → http://localhost:8000/docs       (Swagger UI)
# → http://localhost:8000/llm/status (LLM config status, secret-free)
```

### Renderer

Remotion is invoked as a subprocess by the API render route. No long-running renderer server is required for the demo.

```bash
# Optional: open Remotion Studio to iterate on layouts
npm run dev --workspace apps/renderer
```

---

## Full local demo path

Once both servers are up at `:3000` (web) and `:8000` (api), every step of the pipeline is driven from the homepage:

1. **Upload Sample Video** — pick a short vertical clip.
2. **Analyze Video** — extracts metadata, samples ~8 frames, detects scenes.
3. **Extract Structure Card** — distills the reusable creative pattern.
4. **Generate Storyboard** — click a recommended prompt chip (or write your own) and submit.
5. **Render Final Video** — renders ~30–90s, then plays inline. The media-used badge shows whether the output used the source video, extracted frames, or fell back to placeholder gradients.

The persistent pipeline panel at the top of the page mirrors current job state at every step.

### Smoke test from the terminal (no UI)

```bash
# Upload a sample
curl -F "file=@/path/to/sample.mp4" http://127.0.0.1:8000/videos/upload

# Run the rest of the pipeline using the returned job_id
JOB=<job_id>
curl -X POST http://127.0.0.1:8000/videos/$JOB/analyze-basic
curl -X POST http://127.0.0.1:8000/videos/$JOB/extract-structure-card
curl -X POST http://127.0.0.1:8000/storyboards/generate \
  -H 'Content-Type: application/json' \
  -d '{"user_prompt":"20s luxury perfume ad","target_duration_seconds":20,"source_job_ids":["'"$JOB"'"]}'

# Use the returned storyboard.id below
SB=<storyboard_id>
curl -X POST http://127.0.0.1:8000/storyboards/$SB/render
# → mp4 at data/renders/<storyboard_id>/final.mp4
```

---

## LLM providers

Configured via `apps/api/.env`:

```env
LLM_PROVIDER=seed       # one of: seed | mock
SEED_API_KEY=...
SEED_MODEL=...
SEED_ENDPOINT_ID=...
# SEED_API_BASE_URL=...  # optional override
```

Set `LLM_PROVIDER=mock` to run the entire pipeline without external LLM calls. Mock mode produces realistic structure cards and storyboards derived from the actual analyzed video so the source-aware renderer still has something to remix. See [apps/api/README.md](apps/api/README.md) for details.

---

## Troubleshooting

### Upload step
- **"File exceeds the 200 MB limit"** — re-encode to a smaller clip; the MVP cap is 200 MB.
- **Upload returns 415** — the file is not detected as `video/*`. Convert to mp4 first.

### Analyze step
- **Analysis hangs or 500s** — OpenCV / PySceneDetect couldn't read the file. Try re-encoding to standard h.264 mp4 (`ffmpeg -i in.mov -c:v libx264 -crf 22 out.mp4`).
- **0 frames extracted** — the source is shorter than the sampling interval (~2s/frame). Use a clip ≥4s long.

### Structure card extraction
- **502 with `Seed returned HTTP 401`** — your `SEED_API_KEY` is invalid. Either fix it in `apps/api/.env` or set `LLM_PROVIDER=mock` and restart the API.
- **422 validation error** — the live LLM returned malformed JSON. Re-extract; if it persists, switch to mock mode for the demo and report the bad payload.

### Storyboard generation
- **404 "no structure cards found"** — extract a structure card first.
- **422 validation error** — same as above; retry or fall back to mock.

### Render step
- **503 "Renderer not ready"** — `npm install --workspace apps/renderer` hasn't been run, or the Chromium download was interrupted. Re-run install.
- **502 "Render subprocess failed"** — open the API logs for the full traceback. Common causes: out-of-memory on tiny machines, or a layout exception. Re-try after fixing.
- **MP4 plays but visuals look placeholder-only** — the storyboard's `source_structure_card_ids` did not resolve to any uploaded job on disk. Re-run the pipeline starting from upload so the card → upload mapping exists.

The full media trace (upload → analysis → card → storyboard → render) is verified end-to-end and described in [docs/demo_script.md](docs/demo_script.md).

---

## Security

- API keys live only in `.env` files (gitignored). `.env.example` files document what's needed.
- Never commit secrets.
- Uploads are validated by content-type prefix and size before being persisted under `data/uploads/`.
- The render route does not call the LLM and never executes user-provided code.
