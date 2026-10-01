# ViralCraft

选择参考结构，上传自己的素材，生成并编辑故事板，然后导出 MP4。

新版位于 `codex/mvp-relaunch`，基于「中文版本」。保留旧 JSON 和成片；旧数据不自动公开，也不会被分配给新访客。

## 运行 MVP

最短路径（无需模型 key，明确标记 mock）：

```bash
docker compose up --build -d app
docker compose exec app python -m app.manage invite
```

打开 http://localhost:8000，用终端生成的一次性邀请码进入工作区。公开中英文样片可直接播放。选择结构卡 → 使用演示素材或上传 ≤30 秒、≤30 MB 视频 → 输入 brief → 生成 → 修改字幕和时长 → 保存 → 导出。Docker 首次构建需要联网下载依赖；运行时已预装浏览器、FFmpeg 和中英文字体。

本机开发（Node 22 / Python 3.12 推荐）：

```bash
npm ci
python3 -m venv apps/api/.venv
apps/api/.venv/bin/pip install -r apps/api/requirements.lock
# 仅在没有 .env 时复制；不要覆盖已有凭据
# cp apps/api/.env.example apps/api/.env
apps/api/.venv/bin/python scripts/make_demo.py
npm run build:web
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage invite
LLM_PROVIDER=mock PYTHONPATH=apps/api apps/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

前端开发可单独 `npm run dev:web`，将 `apps/web/.env.local` 的 `NEXT_PUBLIC_API_BASE_URL` 设为 `http://localhost:8000`。正式静态构建固定请求同源 `/api`。不要使用 `next start` 托管静态导出。

## 配置与部署

凭据只放在 `apps/api/.env` 或云端环境变量。`.env` 路径和相对 `DATA_DIR` 均锚定 `apps/api/`，不依赖启动目录。更改后重启 API。

- 文本规划：`LLM_PROVIDER=seed`、`SEED_API_KEY`、`SEED_MODEL`；可选 `SEED_ENDPOINT_ID` 覆盖为自定义部署。新版 Seed 可设 `SEED_THINKING=disabled`。
- 检索：`DATABASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`；缺失时手动选卡。
- 可选镜头：`SEEDANCE_ENABLED=true`、`SEEDANCE_API_KEY`、`SEEDANCE_MODEL`；默认关闭。
- `GET /api/status` 只返回配置完整性。连接验证独立执行 `PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage check-planner`，会产生一次真实文本请求。

[本地运行、真实集成检查、部署和停机步骤](docs/MVP_RUNBOOK.md)

[可回退发布基线与干净构建](docs/releases/BASELINE.md) · [参考方法库、证据与审核流程](packages/reference-library/README.md)

## 结构

- `apps/api/app/runtime/`：SQLite 会话、资源归属、任务、额度、事件；单 worker 串行。
- `apps/api/app/routes/workspace.py`：受保护的 `/api` 接口与下载。
- `apps/api/app/services/`：分析、规划、版本编辑、pgvector 检索、Seedance 和渲染。
- `apps/web/components/TrialStudio.tsx`：中英工作区、轮询恢复、故事板编辑和导出。
- `packages/schemas/src/workspace.ts`：Python wire JSON 对应的共享 Web / renderer 类型。
- `apps/renderer/`：Remotion 确定性拼装；每次渲染只暂存本任务需要的素材。

新故事板分别保存 `reference_card_ids`（请求）/ `source_structure_card_ids`（结果）和 `target_media_job_id`。参考卡提供结构，目标素材提供画面。修改保存会递增版本；渲染绑定保存快照，输出独立目录，不覆盖旧成片。

## 验证

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m unittest discover -s apps/api/tests -v
npm run typecheck
npm run build:web
apps/api/.venv/bin/python scripts/smoke_trial.py --data-dir /tmp/viralcraft-smoke-new
```

真实 pgvector SQL 集成测试使用独立容器（55432，不修改本机已有 PostgreSQL）：

```bash
docker compose --profile search up -d search
TEST_DATABASE_URL=postgresql://viralcraft:local-test-password@localhost:55432/viralcraft PYTHONPATH=apps/api apps/api/.venv/bin/python -m unittest discover -s apps/api/tests -v
```

这些测试不调用付费模型。SQL 测试向量仅是可确定排序的夹具，不能证明真实 embedding 的语义质量。

## 当前边界

首版主要完成素材重剪与结构迁移。OpenCV / PySceneDetect 提取时间、边界和帧；新的学习任务将最多12张真实JPEG与时间戳传给Seed视觉模型，提取开场、信息推进、采样节奏和字幕布局。静帧不支持音频、准确字幕时长或连续动作判断。旧元数据提取和mock路径保留并分别标记。

公共库包括3张预置模板和3张自制演示的视觉提取卡；后者保存原始提取、观察引用、审核修订和样例视频，已完成AI视觉复核，**尚无真人审核**。三条参考片复用同一生成镜头，用于验证方法抽取，不代表真实爆款、广告效果或跨品类泛化。详见 [参考库验收记录](docs/releases/reference-library-2026-09-30.json)。

2026-09-30 已在本机验证真实 Seed 文本规划、1024 维 embedding + pgvector SQL 检索，以及一个 Seedance 2.5 镜头进入 15 秒 MP4；首页第一条成片对应这次验证，另外两条仍为 mock 规划样片。云端部署、真实用户采用与商业结果尚未验证。详见 [本地验收记录](docs/MVP_RUNBOOK.md#8-真实链路验收记录2026-09-30)。
