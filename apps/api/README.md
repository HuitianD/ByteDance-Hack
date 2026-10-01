# ViralCraft API

FastAPI 单进程 API，使用 SQLite 保存邀请会话、归属、任务、额度和事件。

完整启动、配置和云端说明见 [根 README](../../README.md) 与 [运行手册](../../docs/MVP_RUNBOOK.md)。固定依赖使用 `requirements.lock`。

```bash
# 在仓库根目录
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage invite
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
PYTHONPATH=apps/api apps/api/.venv/bin/python -m unittest discover -s apps/api/tests -v
```

`apps/api/.env` 从固定目录读取，密钥不返回前端。新版接口统一 `/api`，媒体必须携带 HttpOnly session cookie；没有全数据目录静态挂载。

旧 `/videos`、`/storyboards`、`/llm` 同步路由仅为本地兼容保留，默认关闭。不要使用旧 curl 示例绕过 `/api/jobs`。
