# ViralCraft Interview Knowledge Base

> **Purpose:** SDE / AI Engineer interview prep grounded in the **actual ViralCraft monorepo** at `ByteDance-Hack/`.  
> **Rule:** Every major claim is tagged **Verified** (code proves it), **Inferred** (reasonable from architecture), or **Unverified** (not provable from code).  
> **Last audited:** 2026-08-24 against repository files listed throughout this document.

---

## Table of Contents

1. [Executive Summary & Resume Verification](#1-executive-summary--resume-verification)
2. [Product Flow (Code-Reconstructed)](#2-product-flow-code-reconstructed)
3. [Architecture & Data Flow](#3-architecture--data-flow)
4. [Technology Decisions](#4-technology-decisions)
5. [STAR Stories](#5-star-stories)
6. [Long-Form Interview Answers](#6-long-form-interview-answers)
7. [SDE System Design Deep Dives](#7-sde-system-design-deep-dives)
8. [Final Cheat Sheet](#8-final-cheat-sheet)

---

## 1. Executive Summary & Resume Verification

### 1.1 Project identity

| Question | Answer | Tag |
|----------|--------|-----|
| Product name in repo | **ViralCraft** (`package.json` name `viralcraft`, API title `ViralCraft API` in `apps/api/app/main.py:18`) | **Verified** |
| Strafe / GearUp in codebase | Not found in source; repo is self-contained as ViralCraft | **Verified** (absence) |
| "Launched" / production users | No deployment config, auth, or metrics in repo | **Unverified** |

### 1.2 Resume bullet #1 — line-by-line

**Original:**

> Built and launched ViralCraft in three weeks, an AI video platform using ByteDance Seed, OpenCV, PySceneDetect, FastAPI, and Remotion to analyze viral advertisements and convert editable Storyboard JSON into deterministic videos.

| Claim | Verdict | Evidence |
|-------|---------|----------|
| Built ViralCraft | **Fully supported** | Full monorepo: `apps/web`, `apps/api`, `apps/renderer`, `packages/schemas`, `packages/prompts` |
| "in three weeks" | **Unverified** | No git history analysis in this doc; **you must confirm timeline orally** |
| "launched" | **Partially supported** | Runnable locally (`README.md`); no prod deploy artifacts (no Docker/K8s/CI) | 
| ByteDance Seed | **Partially supported** | `SeedClient` in `apps/api/app/llm/seed_client.py` — **text/JSON chat completions only**, not video generation API |
| OpenCV | **Fully supported** | `apps/api/app/services/video_analysis.py` — metadata + frame extraction via `cv2.VideoCapture` |
| PySceneDetect | **Fully supported** | Same file: `ContentDetector()` via `scenedetect.detect`; fallback `time_based` |
| FastAPI | **Fully supported** | `apps/api/app/main.py`, routers under `apps/api/app/routes/` |
| Remotion | **Fully supported** | `apps/renderer/`, `render.mjs`, `@remotion/bundler` + `@remotion/renderer` |
| "analyze viral advertisements" | **Partially supported** | Generic short-video analysis + structure extraction; not ad-domain-specific ML unless LLM enriches StructureCard |
| "editable Storyboard JSON" | **Partially supported** | JSON persisted to `data/knowledge_base/storyboards/{id}.json`; **no in-app editor** in `apps/web` |
| "deterministic videos" | **Fully supported** | Remotion renders from fixed JSON + `staticFile()` media paths (`apps/renderer/render.mjs`) |

**Suggested safer wording (bullet #1):**

> Built ViralCraft, a local-first AI short-video **structure transfer** pipeline using FastAPI, OpenCV, PySceneDetect, a ByteDance Seed (Volcano Ark) **LLM adapter**, and Remotion. The system analyzes uploaded sample videos, extracts reusable Structure Cards, generates Storyboard JSON, and renders frame-deterministic mp4s that reuse source footage with composited captions and motion graphics.

**Suggested stronger wording (if you can claim Seed works in your env):**

> …integrated ByteDance Seed (Doubao via Volcano Ark `chat/completions`) to distill Structure Cards and generate topic-specific Storyboard JSON, validated with Pydantic before deterministic Remotion rendering.

---

### 1.3 Resume bullet #2 — line-by-line

**Original:**

> Designed a PostgreSQL/pgvector retrieval layer for hooks, pacing, narrative structures, CTAs, and reusable assets, grounding LLM-generated storyboards in relevant advertising patterns while preserving user control over timing, copy, footage, and effects.

| Claim | Verdict | Evidence |
|-------|---------|----------|
| PostgreSQL | **Unverified / Not in code** | Grep: no `postgres`, `sqlalchemy`, `psycopg` in `apps/api/requirements.txt` or services |
| pgvector | **Unverified / Not in code** | Only mentioned as future in `docs/architecture.md:66`, `docs/demo_script.md:180`, `.cursor/rules/viralcraft-project.mdc:59` |
| "retrieval layer" | **Partially supported** | `select_structure_cards()` in `apps/api/app/services/storyboard.py:79-130` — **filesystem** lookup by `source_job_ids` or **most recent 1–3 cards by mtime**, not vector search |
| hooks, pacing, narrative, CTA | **Partially supported** | Fields on `StructureCard`: `hook_type`, `narrative_flow`, `editing_atoms`, `reusable_rules` (`apps/api/app/schemas/structure_card.py`) — stored in JSON files, not indexed columns |
| reusable assets | **Partially supported** | Uploads + frames on disk; `resolve_media_assets()` maps cards → video/frames (`apps/api/app/services/media_assets.py`) |
| grounding LLM storyboards | **Partially supported** | Selected cards serialized into prompt (`packages/prompts/generate_storyboard.md`, `build_generate_prompt`) |
| user control over timing/copy/footage/effects | **Partially supported** | Storyboard JSON fields exist; user can edit JSON on disk and re-render; **UI has no edit form**; timing normalized server-side in `_normalize_scenes()` |

**Do NOT say in interviews:** "We use pgvector in production" or "PostgreSQL retrieval layer is implemented."

**Suggested safer wording (bullet #2):**

> Designed a **Structure Card knowledge base** (local JSON + filesystem retrieval) capturing hooks, pacing atoms, narrative flow, and reusable rules from analyzed videos. Structure Cards are injected into LLM prompts to ground Storyboard generation, while Storyboard JSON preserves user control over scene timing, copy, layouts, and source footage mapping into Remotion.

**Suggested stronger wording (only after you build pgvector):**

> …migrated retrieval to PostgreSQL + pgvector for semantic matching of briefs to Structure Cards (planned; currently filesystem + mtime fallback in MVP).

---

### 1.4 Critical correction: what ByteDance Seed actually does here

**Verified:** Seed is used exclusively as an **LLM for JSON/text**, not as a **video generator**.

- Factory: `apps/api/app/llm/factory.py:21-37` — `seed` → `SeedClient`
- HTTP: `POST /chat/completions` to Volcano Ark (`seed_client.py:206`, default base `https://ark.cn-beijing.volces.com/api/v3`)
- Payload uses `endpoint_id` as `model` field (`seed_client.py:186`)
- Used by: `extract_structure_card()` and `generate_storyboard()` when `provider_name != "mock"`

**Verified:** **Mock mode bypasses Seed entirely** for structure cards and storyboards:

- `structure_card.py:214-215` — `if llm_client.provider_name == "mock": build_mock_structure_card_data(...)`
- `storyboard.py:365-370` — same for `build_mock_storyboard_data(...)`
- Mock storyboard title prefix: `"Mock storyboard: ..."` (`storyboard.py:278`)

**Inferred:** If a demo output shows `Mock storyboard:` in the title, the API was on **`LLM_PROVIDER=mock`** at generation time, regardless of current `.env`.

**Unverified:** Whether your Seed credentials successfully return valid StructureCard/Storyboard JSON in your environment (401 errors documented in `README.md` troubleshooting).

---

## 2. Product Flow (Code-Reconstructed)

### 2.1 User inputs

| Input | Supported? | Evidence |
|-------|------------|----------|
| Upload sample **video** | **Yes** | `POST /videos/upload` — `apps/api/app/routes/videos.py:104-166` |
| Text **prompt/brief** | **Yes** | `StoryboardGenerateRequest.user_prompt` — max 2000 chars (`storyboard.py:101`) |
| Product/catalog metadata | **No dedicated schema** | Only free-text `user_prompt` |
| Multiple reference videos per storyboard | **Partial** | `source_job_ids: Optional[List[str]]` can list multiple jobs; each must have a saved structure card |
| Image-only upload | **No** | Content-type must start with `video/` (`videos.py:115`) |

**File limits — Verified:**

- Max upload: **200 MB** (`videos.py:25`, `MAX_UPLOAD_BYTES`)
- Extensions: `.mp4`, `.mov`, `.webm`, `.mkv`, `.avi`, `.m4v`, `.mpeg`, `.mpg` (`videos.py:32`)

**Storage — Verified:**

- Upload: `data/uploads/{job_id}/original.{ext}` (`videos.py:127`)
- Frames: `data/frames/{job_id}/frame_NNN.jpg` (`video_analysis.py:70-73`)
- Analysis JSON: `data/knowledge_base/{job_id}/video_analysis.json` (`videos.py:211-213`)
- Structure card: `data/knowledge_base/{job_id}/structure_card.json` (extract route)
- Storyboard: `data/knowledge_base/storyboards/{storyboard_id}.json` (`storyboard.py:425-432`)
- Render output: `data/renders/{storyboard_id}/final.mp4` (`render.py:54-55`)
- Sidecar: `data/renders/{storyboard_id}/media_assets.json` (`render.py:214-217`)

---

### 2.2 Step 2 — Video analysis (non-LLM)

**OpenCV — Verified** (`video_analysis.py`):

| Responsibility | Implementation |
|----------------|----------------|
| Metadata | `_read_metadata()` — fps, width, height, total_frames, duration (`131-156`) |
| Frame sampling | Every **2.0s**, max **12** frames (`29-30`, `_extract_frames`) |
| JPEG write | `cv2.imwrite`, quality 85 (`197-198`) |

**PySceneDetect — Verified** (`221-244`):

| Item | Detail |
|------|--------|
| Algorithm | `ContentDetector()` from `scenedetect` |
| API | `detect(str(video_path), ContentDetector())` |
| Output | `SceneSegment` list with `scene_{i:03d}`, start/end seconds |
| Method tag | `scene_detection_method: "pyscenedetect"` or `"time_based"` |

**Fallback — Verified:** `_time_based_scenes()` — **3.0s** segments (`31`, `247-264`) when PySceneDetect fails.

**NOT extracted — Verified by absence:**

- Audio analysis / transcription
- Motion vectors / optical flow
- On-video subtitle OCR
- Transition type classification (cut vs fade) from pixels
- LLM/VLM frame understanding in analyze-basic route

**Scene `role` field (hook/reveal/payoff):** Optional on `SceneSegment` (`video.py:48-52`) — **not populated** by basic analyzer.

---

### 2.3 Step 3 — Structure Card extraction

**Pipeline — Verified** (`structure_card.py`):

1. Load `video_analysis.json`
2. Build prompt from `packages/prompts/extract_structure_card.md`
3. **Mock:** `build_mock_structure_card_data()` — rule-based from scene count, duration, resolution
4. **Seed:** `llm_client.generate_json()` → validate `StructureCard` Pydantic model
5. Persist + return

**StructureCard schema — Verified** (`structure_card.py:30-60`):

- `pattern_name`, `summary`, `hook_type`, `narrative_flow`, `visual_style`
- `editing_atoms[]` — `kind`, `duration_seconds`, `notes`
- `reusable_rules[]`
- `source_video_job_id`, `source_segments[]`

---

### 2.4 Step 4 — Storyboard JSON (critical IR)

**Schema — Verified** (`apps/api/app/schemas/storyboard.py`, wire format snake_case):

**Storyboard (top level):**

| Field | Purpose |
|-------|---------|
| `id` | UUID |
| `title` | Short title |
| `user_prompt` | Original brief |
| `target_duration_seconds` / `actual_duration_seconds` | Length control |
| `fps`, `width`, `height` | Defaults 30, 1080×1920 (`DEFAULT_*`) |
| `scenes[]` | Ordered scenes |
| `source_structure_card_ids[]` | Lineage |

**StoryboardScene:**

| Field | In schema? | Used by Remotion? |
|-------|------------|-------------------|
| `scene_id` | Yes | Yes — React keys, debug |
| `start_time`, `end_time`, `duration_seconds` | Yes | Yes — `Series.Sequence` duration |
| `layout` | Yes | Yes — `normalizeLayout()` → 6 canonical layouts |
| `text` | Yes | Yes — `Caption` components |
| `visual_description` | Yes | Placeholder fallback text |
| `animation` | Yes | `applyAnimation()` tokens |
| `transition` | Yes | `applyTransitionIn()` |
| `asset_prompt` | Yes | Not generative in MVP — overlay hint only |
| `source_structure_card_id` | Yes | Metadata / lineage |
| `source_editing_atoms` | Yes | UI badges |
| **`asset` (path/URL)** | **No** | Media comes from `mediaAssets` sidecar, not per-scene asset field |
| **`music` / `audio`** | **No** | Not in schema |
| **`camera_motion`** | **No** | Approximated via animation tokens (`ken-burns`, etc.) |
| **`effect` (VFX)** | **No** | Out of MVP scope |
| **`captionStyle`** | **No** | Hardcoded in `Caption.tsx` |

**Why Storyboard JSON is the IR — Verified design intent:**

- README + project rules: no prompt-to-pixels; chain is storyboard → Remotion (`README.md:7-11`)
- LLM output validated then **duration-normalized** deterministically (`_normalize_scenes`, `storyboard.py:303-346`)
- Render route does **not** call LLM (`render.py` docstring, `storyboards.py:103-141`)

**Can users edit fields?**

| Field | Editable how? | Tag |
|-------|---------------|-----|
| timing | Edit JSON → re-render; server may re-normalize on **regenerate** only | **Partial** |
| copy (`text`) | Edit JSON on disk → re-render | **Verified** (manual) |
| footage | Indirect — tied to `source_structure_card_ids` → `media_assets.json` resolution | **Partial** |
| asset per scene | No `asset` field; footage from upload job | **Partial** |
| effect / transition | Edit JSON `animation`/`transition` tokens | **Verified** (manual) |
| In UI | Display only in `StoryboardStep.tsx` — **no edit controls** | **Verified** |

---

### 2.5 Retrieval / RAG

**Verdict: NOT pgvector RAG. Filesystem card selection only.**

**Verified** — `select_structure_cards()` (`storyboard.py:79-130`):

1. If `source_job_ids` provided → load `data/knowledge_base/{job_id}/structure_card.json` for each
2. Else → scan `knowledge_base/*/` for cards, sort by **mtime**, take **1–3** most recent (`_MAX_RECENT_CARDS = 3`)

**NOT present — Verified by absence:**

- Embedding generation
- Vector dimension / similarity metric
- SQL schema / migrations
- Top-K semantic search
- Chroma/pgvector client code

**Prompt grounding — Verified:**

- Cards JSON embedded in `generate_storyboard.md` under `## Structure Cards`
- `build_generate_prompt()` substitutes `{{user_prompt}}`, `{{target_duration_seconds}}`, `{{retrieved_cards}}`

**Interview phrasing:** Call it **"structure card grounding via prompt injection"**, not **"RAG with pgvector"**, unless you implement the latter.

---

### 2.6 Video generation (Seed clarification)

**Verified: Seed does NOT generate video pixels in this codebase.**

There is no:

- Seed video/I2V/T2V API client
- Polling for async video jobs from Seed
- Download of model-generated mp4 from Seed

**Actual video output path:**

1. User upload + extracted frames = visual material
2. LLM (Seed or mock) = **Storyboard JSON text/copy**
3. Remotion = **final mp4** compositing

**Mock/stub modes — Verified:**

| Mode | Trigger | Behavior |
|------|---------|----------|
| `LLM_PROVIDER=mock` | `apps/api/.env` | Deterministic StructureCard + Storyboard synthesizers |
| Placeholder visuals | No media resolved | `PlaceholderVisual.tsx` gradient fallback |
| `MockClient.generate_json` | If ever called directly | Returns `{ok, echo}` stub — **not** used for product paths (bypassed earlier) |

---

### 2.7 Remotion rendering

**Entry — Verified:**

- CLI: `apps/renderer/render.mjs`
- Composition: `Storyboard` in `apps/renderer/src/Root.tsx`
- React tree: `StoryboardComposition` in `Storyboard.tsx`

**Props — Verified:**

```typescript
{ storyboard, mediaAssets?, debugOverlay? }
```

(`Storyboard.tsx:24-34`, `render.mjs` merges `mediaAssets` into `inputProps`)

**Canvas — Verified:**

- Default **1080×1920**, **30 fps** (`storyboard.py:18-21`, `Root.tsx` `calculateMetadata`)

**Layout mapping — Verified:**

| Canonical layout | Component |
|------------------|-----------|
| `hook_title` | `HookTitle.tsx` |
| `text_over_media` | `TextOverMedia.tsx` |
| `feature_card` | `FeatureCard.tsx` |
| `split_compare` | `SplitCompare.tsx` |
| `cta_card` | `CtaCard.tsx` |
| `default_scene` | `DefaultScene.tsx` |

Normalizer: `apps/renderer/src/util/layout.ts` — aliases LLM tokens to canonical set.

**Source-aware media — Verified:**

- `resolve_media_assets()` → `media_assets.json` (`media_assets.py`)
- Remotion `publicDir` = `DATA_DIR`; paths via `staticFile()` (`render.mjs`, `MediaContext.tsx`)
- `SourceMedia.tsx` + `sceneMedia.ts` — per-scene video offset, frame stride, Ken Burns, blur-parallax
- `RenderMediaSummary` on API response (`render_job.py:24-52`)

**Render execution — Verified:**

- **Local subprocess** from API: `asyncio.create_subprocess_exec(node, render.mjs, ...)` (`render.py:112-136`)
- **Not** Remotion Lambda (no `@remotion/lambda` in `package.json`)
- Timeout: **600s** (`render.py:32`)
- Sync HTTP: handler **awaits** full render before returning `RenderJob`

**Output — Verified:**

- `data/renders/{storyboard_id}/final.mp4`
- Served at `/static/renders/...` via FastAPI `StaticFiles` (`main.py:47-51`)

**Failure handling — Verified:**

- Non-zero exit → `RenderError` with stderr tail (`render.py:204-210`, `storyboards.py:133-141`)
- Frontend maps 502/503/404 to friendly strings (`RenderStep.tsx` `formatRenderError`)

---

## 3. Architecture & Data Flow

### 3.1 Mermaid diagram

```mermaid
flowchart TB
  subgraph Web["apps/web (Next.js)"]
    UI[WorkflowSection / 5 Steps]
    APIClient[lib/api.ts]
  end

  subgraph API["apps/api (FastAPI)"]
    R1[POST /videos/upload]
    R2[POST /videos/{id}/analyze-basic]
    R3[POST /videos/{id}/extract-structure-card]
    R4[POST /storyboards/generate]
    R5[POST /storyboards/{id}/render]
    VA[video_analysis.py<br/>OpenCV + PySceneDetect]
    SC[structure_card.py]
    SB[storyboard.py]
    MA[media_assets.py]
    RD[render.py]
    LLM[llm/factory → SeedClient | MockClient]
  end

  subgraph Data["data/ (local filesystem)"]
    UPL[uploads/]
    FR[frames/]
    KB[knowledge_base/]
    REN[renders/]
  end

  subgraph Renderer["apps/renderer (Remotion)"]
    CLI[render.mjs]
    COMP[StoryboardComposition]
    OUT[final.mp4]
  end

  UI --> APIClient --> R1 & R2 & R3 & R4 & R5
  R1 --> UPL
  R2 --> VA --> FR
  R2 --> KB
  R3 --> LLM
  R3 --> KB
  R4 --> LLM
  R4 --> KB
  R5 --> MA
  R5 --> CLI
  CLI --> COMP --> OUT
  MA --> CLI
  UPL & FR --> CLI
  OUT --> REN
  REN -->|/static| UI
```

### 3.2 API routes summary

| Method | Path | Handler file | Sync/async |
|--------|------|--------------|------------|
| GET | `/health` | `main.py:38` | sync |
| GET | `/llm/status` | `routes/llm.py:36` | sync |
| POST | `/videos/upload` | `routes/videos.py:110` | async |
| POST | `/videos/{job_id}/analyze-basic` | `routes/videos.py:179` | sync (threadpool) |
| POST | `/videos/{job_id}/extract-structure-card` | `routes/videos.py` | async |
| POST | `/storyboards/generate` | `routes/storyboards.py:45` | async |
| POST | `/storyboards/{storyboard_id}/render` | `routes/storyboards.py:108` | async (blocks on subprocess) |

---

## 4. Technology Decisions

For each: **What · Where · Why · Alternatives · Trade-off · Improve · Proof**

### 4.1 Next.js + React + TypeScript

| | |
|-|-|
| **What** | React 18 SPA-style app with Next.js 14 App Router |
| **Where** | `apps/web/` — `app/page.tsx`, `components/*`, `lib/api.ts`, `lib/types.ts` |
| **Why selected** | Monorepo alignment with Remotion (React); typed API client; fast demo UI |
| **Alternatives** | Vite+React, Remix |
| **Trade-off** | No SSR need for demo; minimal dependencies (no shadcn in `package.json`) |
| **Improve** | Storyboard editor route; Remotion Player preview before render |
| **Proof** | `apps/web/package.json` — `next@14`, `react@18`, `typescript` |

### 4.2 FastAPI + Pydantic

| | |
|-|-|
| **What** | Async Python API with typed request/response models |
| **Where** | `apps/api/app/` — routers, `schemas/`, `services/` |
| **Why** | Fast iteration for video pipeline; native OpenCV/PySceneDetect; OpenAPI docs |
| **Alternatives** | Django, Node Express |
| **Trade-off** | Sync analyze route uses threadpool; render blocks event loop up to 600s |
| **Improve** | Celery/RQ for render jobs; background analysis queue |
| **Proof** | `requirements.txt`: `fastapi`, `pydantic`, `pydantic-settings`; `main.py` |

### 4.3 OpenCV (`opencv-python`)

| | |
|-|-|
| **What** | Video I/O and frame extraction |
| **Where** | `video_analysis.py` — `_read_metadata`, `_extract_frames` |
| **Why** | Lightweight, no FFmpeg Python binding required for MVP metadata/frames |
| **Alternatives** | FFmpeg CLI, moviepy, PyAV |
| **Trade-off** | No audio; codec edge cases need re-encode |
| **Improve** | FFmpeg for audio strip / proxy generation |
| **Proof** | `requirements.txt:10`, `import cv2` |

### 4.4 PySceneDetect

| | |
|-|-|
| **What** | Content-based scene boundary detection |
| **Where** | `video_analysis.py:228-230` — `ContentDetector()` |
| **Why** | Better segments than fixed intervals when it works |
| **Alternatives** | FFmpeg scene filter, TransNetV2 |
| **Trade-off** | try/except → 3s time-based fallback; no threshold tuning exposed |
| **Improve** | Expose detector threshold; persist `role` labels via LLM |
| **Proof** | `requirements.txt:11`, `scene_detection_method` field |

### 4.5 ByteDance Seed (Volcano Ark LLM)

| | |
|-|-|
| **What** | HTTP LLM client for JSON/text — **not video gen** |
| **Where** | `seed_client.py`, `factory.py`, used in `structure_card.py`, `storyboard.py` |
| **Why** | Hackathon / ByteDance ecosystem; OpenAI-compatible chat API |
| **Alternatives** | OpenAI, Anthropic, local Ollama — adapter pattern supports swap |
| **Trade-off** | `response_format=json_object` not used (HTTP 400); fence-stripping needed |
| **Improve** | Retry/backoff; structured output when model supports it |
| **Proof** | `SeedClient._post_chat`, `DEFAULT_SEED_BASE_URL`, env vars in `config.py:54-60` |

### 4.6 LLM adapter + Mock

| | |
|-|-|
| **What** | `LLMClient` ABC + `SeedClient` + `MockClient` |
| **Where** | `apps/api/app/llm/` |
| **Why** | Demo without API keys; provider swap without product logic changes |
| **Alternatives** | LiteLLM unified gateway |
| **Trade-off** | Mock storyboard copy is placeholder (`Development`, `Try it now`) |
| **Improve** | Topic-aware mock synthesizer for stable demos |
| **Proof** | `base.py`, `mock_client.py:16`, `storyboard.py:365-370` |

### 4.7 Remotion

| | |
|-|-|
| **What** | React-based programmatic video renderer |
| **Where** | `apps/renderer/` — compositions, layouts, `render.mjs` |
| **Why** | Frame-deterministic; Storyboard JSON maps 1:1 to React components |
| **Alternatives** | FFmpeg drawtext filters, After Effects scripting, Motion Canvas |
| **Trade-off** | Heavy Chromium bundle; local render blocks API |
| **Improve** | Remotion Lambda; render queue |
| **Proof** | `remotion@4.0.235`, `Storyboard.tsx`, `render.mjs` |

### 4.8 PostgreSQL / pgvector

| | |
|-|-|
| **What** | **Not implemented** |
| **Where** | Documented as future only |
| **Why N/A** | MVP uses `data/` JSON files |
| **Proof** | Absence in code; mentions in `docs/architecture.md` |

### 4.9 Storage (actual)

| | |
|-|-|
| **What** | Local filesystem under `DATA_DIR` (default `../../data`) |
| **Where** | `config.py:52`, all `services/*` persist paths |
| **Why** | Zero infra for hackathon MVP |
| **Trade-off** | No multi-user isolation; no concurrent write safety |
| **Improve** | S3 + Postgres metadata |

---

## 5. STAR Stories

> **Note:** Timeboxed claims (e.g. "three weeks") are **Unverified** — mark as YOUR oral confirmation.

### STAR 1 — End-to-end MVP with explicit minimal loop

**Situation:** Need a demo proving structure transfer from sample ad → new brief → mp4, without uncontrolled text-to-video.

**Task:** Wire upload, analysis, structure card, storyboard, Remotion render, observable UI.

**Action (code-backed):**

- Monorepo scaffold: `apps/web`, `apps/api`, `apps/renderer`, `packages/schemas`, `packages/prompts`
- Five API endpoints + five UI steps (`WorkflowSection.tsx`)
- LLM adapter with mock fallback (`factory.py`)
- Source-aware render path (`media_assets.py` → `render.mjs` → `SourceMedia.tsx`)

**Result:** Runnable pipeline; `README.md` smoke curl sequence; Pipeline panel shows per-step status.

**You must confirm orally:** Timeline, team size, deployment.

**Code evidence:** `README.md:111-141`, `WorkflowSection.tsx`, `routes/*.py`

---

### STAR 2 — Storyboard JSON preserves user control

**Situation:** LLM outputs are probabilistic; brand teams need editable timing/copy before final render.

**Task:** Insert validated JSON IR between LLM and pixels.

**Action:**

- Pydantic `Storyboard` / `StoryboardScene` schemas (`storyboard.py`)
- Duration normalization (`_normalize_scenes`) so render length is deterministic
- Remotion reads JSON only — render route never calls LLM
- Persisted JSON enables manual edit + re-render

**Result:** Same storyboard file → same Remotion output; change JSON → re-render without LLM cost.

**Gap to acknowledge:** No GUI editor yet; control is via JSON file or regenerate.

**Code evidence:** `storyboard.py:303-346`, `render.py:173-190`, project rules `.cursor/rules/viralcraft-project.mdc`

---

### STAR 3 — Grounding generation (conservative: NOT pgvector)

**Situation:** Generic LLM storyboards ignore reference ad structure.

**Task:** Ground generation in extracted patterns.

**Action (actual MVP):**

- Extract `StructureCard` from `VideoAnalysis` (LLM or mock)
- Select cards by job id or recent mtime (`select_structure_cards`)
- Inject full card JSON into `generate_storyboard.md` prompt
- Scenes carry `source_structure_card_id` + `source_editing_atoms` for lineage

**Result:** Scene layouts mirror card atoms (hook_title, feature_card, cta_card rotation in mock).

**Do NOT claim:** pgvector semantic retrieval.

**Future version (if built):** Embed `pattern_name + summary + hook_type`, top-K via pgvector, metadata filters on aspect ratio/duration.

**Code evidence:** `storyboard.py:79-130`, `packages/prompts/generate_storyboard.md`, `StructureCard` schema

---

### Optional STAR 4 — Source-aware rendering

**Action:** Map `source_structure_card_ids` → `source_video_job_id` → upload + frames; pass `mediaAssets` to Remotion; expose `RenderMediaSummary`.

**Proof:** `media_assets.py:134-160`, `render_job.py:24-52`, `SourceMedia.tsx`

---

## 6. Long-Form Interview Answers

Format: **Logic (中文)** · **30s EN** · **90s EN** · **Follow-ups** · **Evidence**

---

### Q: Walk me through ViralCraft.

**逻辑：** 五步法 + 中间表示 + 素材复用 + 非 VFX。

**30s EN:**  
"ViralCraft transfers editing structure from a sample short video to a new brief. Users upload a clip, we analyze it with OpenCV and PySceneDetect, extract a reusable Structure Card via an LLM, generate a Storyboard JSON from the brief plus that card, and render deterministically with Remotion—reusing the uploaded footage as backgrounds with motion graphics and captions on top."

**90s EN:** Expand with: mock vs seed, filesystem card selection (not pgvector), sync render subprocess, 200MB limit, MVP excludes pixel VFX.

**Follow-ups:** How is this different from Runway/Sora? → structure IR + user footage, not model-generated pixels.

**Evidence:** `README.md`, pipeline routes, `Storyboard.tsx`

---

### Q: What problem does it solve?

**30s EN:** "Creative teams can't reuse viral *editing structure* at scale; ViralCraft codifies hook/pacing/atoms into Structure Cards and reapplies them to new topics with controlled Storyboard JSON before render."

**Evidence:** Project rules, `StructureCard` schema

---

### Q: What did you personally build?

**Unverified** — codebase alone cannot attribute authorship.

**Safe answer:** "I built/contributed to the monorepo spanning FastAPI services, Next.js workflow UI, Remotion layouts, LLM adapter, and source-aware render pipeline—exact ownership is [your clarification]."

---

### Q: Why not pure text-to-video?

**30s EN:** "Text-to-video is uncontrollable for brand ads. We separate probabilistic planning (LLM → Storyboard JSON) from deterministic execution (Remotion), so timing, copy, and layout are inspectable and editable."

**Evidence:** `README.md:5-11`, `.cursor/rules/viralcraft-project.mdc:24-26`

---

### Q: Why Storyboard JSON?

**Evidence:** Pydantic schemas, `_normalize_scenes`, render consumes JSON only

---

### Q: Why Remotion?

**30s EN:** "React components give frame-deterministic rendering; each layout is a component driven by schema fields—change JSON, re-render, no LLM call."

**Evidence:** `apps/renderer/src/layouts/*`, `util/animation.ts`

---

### Q: How does PySceneDetect work here?

**Verified:** `ContentDetector` via `scenedetect.detect`; fallback 3s segments; method stored on `VideoAnalysis.scene_detection_method`.

---

### Q: What does OpenCV do?

**Verified:** Metadata + seek-by-timestamp frame grab + JPEG write — not scene detect (that's PySceneDetect).

---

### Q: How is ByteDance Seed integrated?

**30s EN:** "Adapter pattern: `SeedClient` posts to Volcano Ark `/chat/completions` with endpoint id as model, for `generate_json` on structure card and storyboard prompts—not for video generation."

**Follow-up:** 401 errors → README troubleshooting; mock mode for local demo.

**Evidence:** `seed_client.py`, `factory.py`, `routes/llm.py`

---

### Q: How does the retrieval layer work?

**Honest 30s EN:** "In the MVP, retrieval is filesystem-based: we load Structure Cards by explicit job ids or pick the one to three most recently modified cards. Their JSON is injected into the storyboard prompt. There is no pgvector or PostgreSQL in the current code."

**Evidence:** `storyboard.py:79-130`; absence of pgvector

---

### Q: Why pgvector instead of a separate vector DB?

**Answer:** "We haven't implemented pgvector yet—it's documented as a future option. I'd choose pgvector when Structure Cards share Postgres with metadata; Pinecone/Qdrant if embedding-only scale dominates."

**Evidence:** `docs/architecture.md:66`

---

### Q: How do you preserve user control?

**Partial:** JSON fields for timing/copy/animation; manual JSON edit + re-render; UI displays but doesn't edit; footage via source job linkage.

---

### Q: How do you handle asynchronous rendering?

**Honest:** "Render is synchronous from the HTTP client's perspective—the FastAPI handler awaits a Node subprocess up to 600 seconds. The `RenderJob` schema has queued/running states for future async, but MVP returns only when done."

**Evidence:** `render_job.py:5-7`, `render.py:173-178`

---

### Q: What happens when the model API fails?

**Verified:** `LLMError` → HTTP 502; 401 gets enhanced message in `videos.py`; validation → 422; renderer failures → 502 with stderr tail.

---

### Q: Hardest engineering challenge?

**Suggested (you confirm):** Source-aware Remotion—`staticFile()` + `publicDir`, rejecting `file://` URLs, per-scene treatment in `sceneMedia.ts`, media sidecar contract.

**Evidence:** `render.mjs`, `SourceMedia.tsx`, `media_assets.py`

---

### Q: Production scale / concurrent users?

**Not in code.** Discuss: job queue, object storage, separate render workers, Postgres, tenant isolation.

---

### Q: How would you test?

**Verified gap:** **Zero test files** found (`**/test*` glob empty).

**Suggest:** Pydantic validation tests, `select_structure_cards` unit tests, Remotion smoke render in CI, mock LLM fixtures.

---

## 7. SDE System Design Deep Dives

### 7.1 Video job state machine (target vs current)

**Current MVP — Verified:** `RenderJobStatus` = `queued | running | succeeded | failed | cancelled` but render returns **`succeeded` immediately** after sync subprocess (`render.py:216-225`).

**Production design (interview answer):**

```
uploaded → analyzing → analyzed → extracting_card → ready
→ storyboard_generating → storyboard_ready
→ render_queued → render_running → render_succeeded | render_failed
```

Persist transitions in Postgres; worker claims jobs with `FOR UPDATE SKIP LOCKED`.

---

### 7.2 Idempotent render

**Current:** Re-posting `/render` overwrites `final.mp4` (`render.mjs` `overwrite: true`).

**Improve:** Idempotency-Key header; dedupe by `(storyboard_id, storyboard_content_hash)`.

---

### 7.3 Avoid duplicate expensive LLM calls

**Current:** No cache.

**Improve:** Hash `(video_analysis_hash, prompt_template_version)` for structure card; hash `(user_prompt, card_ids, duration)` for storyboard.

---

### 7.4 File lifecycle

**Verified paths:** uploads, frames (wiped on re-analyze), KB JSON, renders.

**Gap:** No TTL cleanup job.

**Security — Verified:** UUID validation on job_id (`videos.py:68-76`) prevents path traversal.

---

### 7.5 Ten concurrent large uploads

**Current:** Streaming write with 1MB chunks; 200MB cap; sync analyze in threadpool.

**Bottleneck:** Disk I/O, CPU for OpenCV/PySceneDetect, blocking render.

**Improve:** Upload to S3 presigned; analyze/render workers; backpressure via queue depth.

---

### 7.6 Storyboard schema versioning

**Current:** `extra="ignore"` on Pydantic models; TS mirrors in `packages/schemas`.

**Improve:** `storyboard_version` field; migrator; renderer layout registry versioned.

---

## 8. Final Cheat Sheet

### 8.1 Ten technical facts (memorize)

1. **Pipeline:** upload → analyze-basic → extract-structure-card → storyboards/generate → storyboards/render (**Verified**)
2. **Analyze is non-LLM:** OpenCV metadata + frames; PySceneDetect `ContentDetector` with 3s fallback (**Verified**)
3. **Seed = LLM JSON/text only**, via `POST /chat/completions`, not video gen (**Verified**)
4. **Mock mode** bypasses Seed for cards + storyboards (**Verified**)
5. **Storyboard JSON** is the IR; Remotion never calls LLM (**Verified**)
6. **Retrieval = filesystem**, 1–3 recent cards or explicit job ids — **not pgvector** (**Verified**)
7. **Render = local Node subprocess**, 600s timeout, sync HTTP (**Verified**)
8. **Source-aware:** `media_assets.json` + `staticFile()` + `SourceMedia` (**Verified**)
9. **Defaults:** 1080×1920, 30fps, 20s target duration (**Verified**)
10. **No automated tests, no Docker, no Postgres in repo** (**Verified**)

---

### 8.2 Five strongest interview highlights

1. **Structure transfer IR** — Storyboard JSON decouples LLM from pixels  
2. **Provider-agnostic LLM adapter** — Seed + mock, product logic isolated  
3. **Dual-schema discipline** — `packages/schemas` + Pydantic mirrors  
4. **Source-aware Remotion** — real upload/frames as backgrounds, honest fallback  
5. **End-to-end observable demo UI** — Pipeline panel, step artifacts, media summary badge  

---

### 8.3 Ten likely follow-up questions

1. "Where's pgvector?" → Not implemented; filesystem grounding  
2. "Does Seed generate video?" → No, only JSON/copy  
3. "How do users edit storyboard?" → JSON on disk today; UI is read-only  
4. "Is render async?" → Blocking MVP; schema ready for async  
5. "How do you test?" → No tests yet; propose plan  
6. "PySceneDetect threshold?" → Default ContentDetector; not exposed  
7. "Multi-tenant?" → Not supported; local `data/`  
8. "Why Remotion over FFmpeg?" → React layout system + deterministic preview  
9. "What if LLM returns bad JSON?" → Pydantic 422  
10. "Production deploy?" → Not in repo  

---

### 8.4 Five things NOT to overclaim

1. ❌ "PostgreSQL/pgvector retrieval layer"  
2. ❌ "Seed generates video" / "ByteDance video model API"  
3. ❌ "Fully editable in UI" (only JSON-level / regenerate)  
4. ❌ "Production-launched at scale" (no deploy/auth/metrics)  
5. ❌ "Deep ad analysis" (basic CV + optional LLM structure; no VLM on frames in analyze-basic)  

---

### 8.5 Numbers & facts YOU must supply orally

| Item | Status |
|------|--------|
| Built in three weeks | **Unverified** |
| Your specific contributions | **Unverified** |
| Seed works in prod vs mock demos | **Unverified** |
| User counts / launch venue (GearUp etc.) | **Unverified** |
| Typical render time on your machine | **Measured once ~25–90s** in dev — cite as anecdotal |
| Team size | **Unverified** |

---

### 8.6 Recommended English project pitch (30–45s)

> "ViralCraft is an AI-assisted **structure transfer** engine for short-form ads. Instead of generating video directly from a prompt, we analyze an uploaded reference clip with OpenCV and PySceneDetect, distill its hook, pacing, and editing atoms into a reusable Structure Card, and use a ByteDance Seed LLM to produce a validated Storyboard JSON for a new brief. Remotion then renders a deterministic mp4, compositing captions and motion graphics over the user's own footage. The MVP intentionally avoids pixel-level VFX; the innovation is the Storyboard intermediate representation that keeps creative control while still leveraging LLMs for planning."

---

## Appendix A — Key file index

| Area | Path |
|------|------|
| API entry | `apps/api/app/main.py` |
| Upload/analyze/extract | `apps/api/app/routes/videos.py` |
| Storyboard/render routes | `apps/api/app/routes/storyboards.py` |
| OpenCV + PySceneDetect | `apps/api/app/services/video_analysis.py` |
| Structure card service | `apps/api/app/services/structure_card.py` |
| Storyboard service | `apps/api/app/services/storyboard.py` |
| Media resolver | `apps/api/app/services/media_assets.py` |
| Render orchestration | `apps/api/app/services/render.py` |
| Seed LLM client | `apps/api/app/llm/seed_client.py` |
| LLM factory | `apps/api/app/llm/factory.py` |
| Remotion CLI | `apps/renderer/render.mjs` |
| Main composition | `apps/renderer/src/Storyboard.tsx` |
| Source media | `apps/renderer/src/media/SourceMedia.tsx` |
| Frontend workflow | `apps/web/components/WorkflowSection.tsx` |
| API client | `apps/web/lib/api.ts` |
| Prompts | `packages/prompts/*.md` |
| TS schemas | `packages/schemas/src/*.ts` |

---

## Appendix B — LLM mode quick check (for interviews)

```bash
# After starting API:
curl -s http://127.0.0.1:8000/llm/status
```

Interpret:

- `"provider": "seed", "configured": true` → Seed client will be used **unless** mock paths short-circuit only when provider is mock
- Storyboard title prefix **`Mock storyboard:`** → generation definitely used mock synthesizer (`storyboard.py:278`)

Config env vars (names only, **never commit values**): `LLM_PROVIDER`, `SEED_API_KEY`, `SEED_MODEL`, `SEED_ENDPOINT_ID`, optional `SEED_API_BASE_URL` — see `apps/api/app/core/config.py:54-60`, `apps/api/.env.example`.

---

*End of document. Single source of truth for interview prep; revise when codebase changes.*
