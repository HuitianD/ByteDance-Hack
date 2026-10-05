# Utility scripts

从仓库根目录运行：

- `apps/api/.venv/bin/python scripts/make_demo.py`：生成自制 15 秒咖啡素材，安装到 API 和公开示例目录。无外部媒体或 API 调用。
- `apps/api/.venv/bin/python scripts/smoke_trial.py --data-dir /tmp/viralcraft-check --renders 3`：隔离执行邀请码 → 素材 → mock 草稿 → 编辑 → 真实 Remotion MP4 → 授权下载，生成 `smoke-report.json`。需要 Python、Node、已安装的 Chromium。每次选择新的 data-dir 可保证隔离，不改历史文件。

Docker 内可直接 `python scripts/smoke_trial.py --data-dir /tmp/check --renders 3`。使用 HTTPS TestClient 验证生产 cookie。

`verify_live.py` 是独立的收费集成检查，必须显式加 `--allow-paid`。在停止使用同一数据目录的 API 后，依次执行 `draft`、`assets`、`render` 三阶段。它保留真实向量检索、规划、一个生成镜头和成片的证据；重复运行复用已完成阶段。详见 `docs/MVP_RUNBOOK.md`。不要将其加入默认 CI。
