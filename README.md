# ViralCraft

AI-powered short video **structure transfer** engine.

ViralCraft learns reusable creative structure from example short videos and applies that structure to new topics, products, or briefs. Every generated video flows through a structured **storyboard JSON** before rendering — no free-form text-to-video shortcuts.

```
user request + retrieved structure cards
  → storyboard JSON
  → Remotion composition
  → rendered mp4
```

This repository is the initial scaffold. Product logic is intentionally minimal at this stage.

---

## Repository Layout

```
apps/
  web/        # Next.js + TypeScript + Tailwind frontend
  api/        # FastAPI backend
  renderer/   # Remotion video renderer

packages/
  schemas/    # Shared TypeScript schema definitions
  prompts/    # Prompt templates (placeholders)

data/
  uploads/         # Source uploads (gitignored)
  frames/          # Extracted frames (gitignored)
  renders/         # Rendered mp4 outputs (gitignored)
  knowledge_base/  # Saved structure cards (gitignored)

docs/
  architecture.md
  structure_schema.md
  demo_script.md

scripts/    # Utility scripts
```

---

## Prerequisites

- **Node.js** ≥ 20
- **npm** ≥ 10 (workspace support)
- **Python** ≥ 3.11
- **FFmpeg** on PATH (`brew install ffmpeg` on macOS)

---

## First-Time Setup

Clone the repo, then:

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
```

---

## Running Locally

Each app runs in its own terminal.

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
# → http://localhost:8000/docs (Swagger UI)
```

### Renderer (Remotion Studio)

```bash
npm run dev --workspace apps/renderer
# Opens Remotion Studio in the browser
```

To render a placeholder video to mp4:

```bash
npm run render --workspace apps/renderer
# → data/renders/placeholder.mp4
```

---

## What's In This Scaffold

- Frontend homepage showing the 5-step workflow
- FastAPI `/health` endpoint
- Minimal Remotion composition rendering a placeholder video
- Shared placeholder schemas: `VideoAnalysis`, `StructureCard`, `Storyboard`, `RenderJob`
- Empty `data/` subfolders ready for pipeline artifacts
- `.env.example` files (no secrets committed)

Product logic — analysis, retrieval, storyboard generation — is **not** implemented yet.

---

## Security

- API keys live only in `.env` files (gitignored). `.env.example` files document what's needed.
- Never commit secrets.
- Validate all uploads by type and size before processing.
