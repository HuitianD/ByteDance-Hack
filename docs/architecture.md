# Architecture

ViralCraft is split into three apps and two shared packages, coordinated through a typed pipeline that always passes through a structured **Storyboard JSON** before rendering.

```
+--------------+      +-----------------+      +------------------+
|  apps/web    | <--> |   apps/api      | <--> |  apps/renderer   |
|  (Next.js)   |      |   (FastAPI)     |      |   (Remotion)     |
+--------------+      +-----------------+      +------------------+
        \                    |                         /
         \                   |                        /
          +-----> packages/schemas (shared types) <--+
                  packages/prompts (LLM templates)

                          data/
                          ├── uploads/
                          ├── frames/
                          ├── renders/
                          └── knowledge_base/
```

## Apps

### `apps/web` — Next.js frontend
- Drives the demo flow: upload → analysis timeline → save card → generate storyboard → preview/render.
- All API calls go through a centralized typed client (to be added). No scattered untyped `fetch`.
- No API keys client-side. The frontend talks only to `apps/api`.

### `apps/api` — FastAPI backend
- Owns analysis, retrieval, generation, and render orchestration.
- Uses FFmpeg for cut/audio/stitch and OpenCV / PySceneDetect for frames + scene detection.
- Calls LLMs via an adapter (provider-agnostic). Keys come from environment variables.
- Persists artifacts under `data/` keyed by job IDs.

### `apps/renderer` — Remotion renderer
- Compositions accept a `Storyboard` JSON and render scene-by-scene.
- Scenes are driven by typed fields: `duration`, `layout`, `text`, `asset`, `transition`, `animation`, `captionStyle`, `sourceStructureCardId`.
- The current scaffold ships only a `Placeholder` composition.

## Shared Packages

### `packages/schemas`
Single source of truth for TypeScript types. The Pydantic mirrors live in `apps/api`. Schema changes must update both sides + sample JSON.

### `packages/prompts`
Markdown prompt templates with documented input variables. Used by the LLM adapter in the API.

## Pipeline

```
upload (web)
  → POST /videos        (api)            ──► data/uploads/<job>.mp4
  → POST /analyze       (api)            ──► VideoAnalysis JSON
  → POST /structure     (api)            ──► StructureCard saved to KB
  → POST /storyboard    (api)            ──► Storyboard JSON (uses retrieval)
  → POST /render        (api → renderer) ──► data/renders/<job>.mp4
```

All step outputs are observable in the UI.

## Data Storage

Stage-appropriate, lightweight by default:

- Local JSON files for analyses, structure cards, storyboards, render jobs.
- Optional: SQLite for indexes; Chroma (or similar) for embedding retrieval.
- No heavy database introduced unless explicitly requested.

## Security

- Secrets only via `.env` (gitignored). `.env.example` documents required keys.
- Uploaded files validated by type + size before processing.
- No execution of arbitrary user-provided code.

## Out of Scope (for the scaffold)

- Actual analysis / retrieval / generation / render orchestration.
- Auth, multi-tenant data isolation, rate limiting.
- CI/CD.
