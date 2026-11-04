# ViralCraft

Pick a reference structure, upload your own footage, generate and edit a storyboard, then export an MP4.

The current version lives on `codex/mvp-relaunch` and is based on the Chinese release. Existing JSON and finished videos are kept. Legacy data is not published automatically and is not assigned to new visitors.

## Run the MVP

Shortest path (no model key required; mock mode is labeled explicitly):

```bash
docker compose up --build -d app
docker compose exec app python -m app.manage invite
```

Open http://localhost:8000 and enter the workspace with the one-time invite code printed in the terminal. The public Chinese and English sample videos play directly. Choose a structure card → use the demo footage or upload a video of at most 30 seconds and 30 MB → enter a brief → generate → edit captions and timing → save → export. The first Docker build needs network access to download dependencies. The runtime image already includes a browser, FFmpeg, and Chinese and English fonts.

Local development (Node 22 and Python 3.12 recommended):

```bash
npm ci
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -r apps/api/requirements.lock
# Copy only when .env does not already exist; do not overwrite existing credentials
# cp apps/api/.env.example apps/api/.env
apps/api/.venv/bin/python scripts/make_demo.py
npm run build:web
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage invite
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

For frontend development, run `npm run dev:web` on its own and set `NEXT_PUBLIC_API_BASE_URL` in `apps/web/.env.local` to `http://localhost:8000`. The production static build always calls the same-origin `/api`. Do not serve the static export with `next start`.

## Configuration and deployment

Put credentials only in `apps/api/.env` or in cloud environment variables. Both the `.env` path and a relative `DATA_DIR` are anchored to `apps/api/` and do not depend on the process working directory. Restart the API after changes.

- Text planning: `LLM_PROVIDER=seed`, `SEED_API_KEY`, and `SEED_MODEL`. Optionally set `SEED_ENDPOINT_ID` to override a custom deployment. Newer Seed models can use `SEED_THINKING=disabled`.
- Retrieval: `DATABASE_URL`, `EMBEDDING_API_KEY`, and `EMBEDDING_MODEL`. When these are missing, cards are selected manually.
- Optional shots: `SEEDANCE_ENABLED=true`, `SEEDANCE_API_KEY`, and `SEEDANCE_MODEL`. Disabled by default.
- `GET /api/status` reports configuration completeness only. To verify the connection, run `PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage check-planner` separately. That command makes one real text request.

[Local run, real integration checks, deployment, and shutdown](docs/MVP_RUNBOOK.md)

[Rollback-safe release baseline and clean builds](docs/releases/BASELINE.md) · [Reference method library, evidence, and review process](packages/reference-library/README.md)

## Layout

- `apps/api/app/runtime/`: SQLite sessions, resource ownership, jobs, quotas, and events. A single worker runs jobs serially.
- `apps/api/app/routes/workspace.py`: protected `/api` endpoints and downloads.
- `apps/api/app/services/`: analysis, planning, version editing, pgvector retrieval, Seedance, and rendering.
- `apps/web/components/TrialStudio.tsx`: bilingual workspace, polling recovery, storyboard editing, and export.
- `packages/schemas/src/workspace.ts`: shared web and renderer types that match the Python wire JSON.
- `apps/renderer/`: deterministic Remotion composition. Each render stages only the media that job needs.

New storyboards store `reference_card_ids` (the request) and `source_structure_card_ids` (the result) separately from `target_media_job_id`. Reference cards supply structure. Target media supplies the picture. Saving an edit increments the version. A render is bound to a saved snapshot and writes to its own directory, so older finished videos are not overwritten.

## Verification

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m unittest discover -s apps/api/tests -v
npm run typecheck
npm run build:web
apps/api/.venv/bin/python scripts/smoke_trial.py --data-dir /tmp/viralcraft-smoke-new
```

The real pgvector SQL integration tests use a separate container on port 55432 and do not modify an existing local PostgreSQL:

```bash
docker compose --profile search up -d search
TEST_DATABASE_URL=postgresql://viralcraft:local-test-password@localhost:55432/viralcraft PYTHONPATH=apps/api apps/api/.venv/bin/python -m unittest discover -s apps/api/tests -v
```

These tests do not call paid models. The SQL test vectors are deterministic ranking fixtures only. They do not prove the semantic quality of real embeddings.

## Current scope

The first version mainly recuts footage and transfers structure. OpenCV and PySceneDetect extract timing, boundaries, and frames. A new learning job sends up to 12 real JPEGs plus timestamps to the Seed vision model to extract the opening, information progression, sampled pacing, and caption layout. Still frames do not support audio, accurate caption timing, or continuous motion judgment. The older metadata extraction path and the mock path are kept and labeled separately.

The public library includes 3 preset templates and 3 visual extraction cards from in-house demos. The latter store the original extraction, observation references, review revisions, and sample videos. They have completed AI visual review and **have not yet had human review**. The three reference clips reuse the same generated shot to validate method extraction. They do not represent real viral hits, advertising performance, or cross-category generalization. See the [reference library acceptance record](docs/releases/reference-library-2026-09-30.json).

On 2026-09-30, real Seed text planning, 1024-dimensional embedding plus pgvector SQL retrieval, and one Seedance 2.5 shot inside a 15-second MP4 were verified locally. The first finished video on the homepage corresponds to that verification. The other two remain mock planning samples. Cloud deployment, real user adoption, and commercial results have not been verified. See the [local acceptance record](docs/MVP_RUNBOOK.md#8-真实链路验收记录2026-09-30).
