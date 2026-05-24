# ViralCraft API

FastAPI backend for ViralCraft.

## Setup

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configuring the Seed (ByteDance AIGC) API key

The API reads provider config **only** from `apps/api/.env`. Never put keys
in source files, the frontend env, or `.env.example`.

Open `apps/api/.env` and set the three required values:

```env
LLM_PROVIDER=seed
SEED_API_KEY=<your Seed API key>
SEED_MODEL=<model name from your Seed console>
SEED_ENDPOINT_ID=<EP id from your Seed console, e.g. ep-xxxxxxxx-xxxx>
```

`SEED_API_BASE_URL` is **optional**. If you leave it blank, the client
defaults to the Volcano Ark cn-beijing host
(`https://ark.cn-beijing.volces.com/api/v3`). Set it only if your
deployment uses a different region or host:

```env
# Optional override
SEED_API_BASE_URL=https://your-region-host/api/v3
```

`apps/api/.env` is gitignored (verified via `git check-ignore`). To swap
providers later, change `LLM_PROVIDER` and set its keys; product code does
not need to change.

If you want to develop without a key, use:

```env
LLM_PROVIDER=mock
```

The mock client returns deterministic stub responses.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health
- LLM status: http://localhost:8000/llm/status
- Swagger UI: http://localhost:8000/docs

`/llm/status` returns the active provider, whether config is complete, and
the **names** of any missing env vars. It never returns the API key.

## Layout

```
app/
  main.py              # FastAPI app, /health, mounts routers
  core/
    config.py          # Settings (pydantic-settings, reads .env)
  llm/
    base.py            # LLMClient interface, errors
    seed_client.py     # Seed (ByteDance AIGC) client -- TODOs for payload
    mock_client.py     # Keyless stub client
    factory.py         # get_llm_client(settings) -> LLMClient
  routes/
    llm.py             # GET /llm/status
```

## Notes

- Pipeline routes (upload, analyze, retrieve, generate, render) are not yet implemented.
- `seed_client.py` has clearly marked `TODO(seed-*)` sections for the exact
  endpoint path, request payload, response shape, and auth header. Fill
  these in from the official Seed API spec.
- Pydantic mirrors of the shared schemas (`apps/api/app/schemas/`) will be
  added when the first real endpoint that needs them lands.
