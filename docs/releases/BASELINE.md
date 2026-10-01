# Recoverable local MVP baseline

This snapshot preserves the working application before evidence-backed reference
learning is added. `baseline-2026-09-30.json` records the tested scope and SHA-256
hashes of the three public demo MP4s. The original outputs and private integration
state remain under the existing, gitignored `data/` directory.

## Reproduce without secrets or paid calls

From a clean checkout:

```bash
docker build -t viralcraft:baseline .
docker run --rm -e LLM_PROVIDER=mock -e SEEDANCE_ENABLED=false \
  viralcraft:baseline python scripts/smoke_trial.py \
  --data-dir /tmp/viralcraft-baseline-smoke --renders 1
```

The image installs dependencies and its own rendering browser at build time,
builds the web export, and creates the synthetic upload sample. No host `.env`,
`node_modules`, `.venv`, uploaded videos or database are needed. The mock smoke
test covers invitation, sample import, background planning, editing, rendering
and authenticated MP4 retrieval. It does not call an external model.

For an HTTP preview on this machine (not a public deployment):

```bash
docker run --rm -p 127.0.0.1:18081:8000 \
  -e APP_ENV=development -e COOKIE_SECURE=false \
  -e LLM_PROVIDER=mock -e SEEDANCE_ENABLED=false viralcraft:baseline
```

Open `http://localhost:18081`. The public examples need no invitation. The
production configuration retains secure cookies and requires HTTPS.

## Recover safely

The annotated Git tag `baseline/local-mvp-2026-09-30` identifies this snapshot.
To inspect or build it without replacing the current working tree:

```bash
git worktree add --detach /tmp/viralcraft-baseline baseline/local-mvp-2026-09-30
```

Use a fresh data directory for verification. Do not reset, delete or replace
the current private data, credentials, uploads or historical videos. Real model
configuration is documented in `apps/api/.env.example` and `docs/MVP_RUNBOOK.md`;
credentials are never part of this baseline.
