# ViralCraft MVP 运维与演示

## 1. 启动、邀请、停止

仓库根目录运行 `docker compose up --build -d app`。默认 mock；数据保存在 `trial-data` volume。生成邀请码：

```bash
docker compose exec app python -m app.manage invite --quota 3
```

每个邀请码只能兑换一次，会话 7 天；没有邮箱或密码。浏览器刷新后从 SQLite 恢复资源和任务。换浏览器需要新邀请码。历史 JSON 保留在磁盘，不自动出现在访客库。

停止：`docker compose stop app`。恢复：`docker compose start app`。不要使用 `down -v`，它会删除命名卷。备份时先停止服务，然后备份整个 `/var/data`，包括 SQLite 及视频；恢复时使用同一目录。运行中断任务启动后标记失败，可从 UI 重试；Seedance 保留 provider request ID，重试只继续查询已有请求。

## 2. Render 单实例

尚未部署；需要先创建 Render 账号。代码已提供 `Dockerfile` 和 `render.yaml`。

1. 将已审阅的分支推送到 GitHub，在 Render 连接该仓库并以此分支创建 Blueprint。没有推送时，也可在准备好后手动创建 Docker Web Service。
2. 使用 Hobby workspace（无固定订阅费）、单实例 `1c-2g`（旧称 Standard），挂载 1 GB persistent disk 到 `/var/data`。不要横向扩容，不要增加 Uvicorn worker。
3. 设置文本模型变量，或先用 `LLM_PROVIDER=mock` 验收。生产 `APP_ENV=production`、`COOKIE_SECURE=true`、`LEGACY_LOCAL_API=false`；前端与 API 使用同一 HTTPS 域名。健康检查 `/api/health`。
4. 在 Render Shell 执行 `python -m app.manage invite --quota 3`。不要把邀请码写入公开文档或构建日志。
5. 用新浏览器兑换邀请码，完成一次生成、编辑、渲染、下载，再验证三条不同 brief。真实模型失败时先运行 `python -m app.manage check-planner`，不要连续消耗试用额度。
6. 面试后在控制台暂停服务；先下载样片与备份。确认计算实例停机，持久盘仍可能计费。删除服务/磁盘前先备份并人工确认。

费用核对日期：2026-09-29。Render 官方列出 2 GB / 1 CPU 为 $25/月，按运行时间精确到秒计费；1 GB 磁盘 $0.25/月。按 30 天估算，两天约 $1.68，另计构建、带宽、模型和税费。持续整月会超过本次 $20 总预算，必须按演示窗口停止。免费 512 MB 实例无法满足持久盘要求，未作为可靠渲染部署验收。参见 [官方定价](https://render.com/pricing)、[实例配置](https://render.com/docs/compute-plans)。

代码中的次数限制不是账单封顶。模型控制台应另设消费提醒/上限（平台支持时），首次 Seedance 只测一个镜头。

## 3. 模型配置

`apps/api/.env` 和平台环境变量优先于示例文件；进程环境优先于 .env。文本、embedding、视频 client 相互独立。

文本（先恢复）：

```dotenv
LLM_PROVIDER=seed
SEED_API_KEY=
SEED_MODEL=
SEED_ENDPOINT_ID=
# 新版 Seed 的短 JSON 规划可关闭思考；旧模型不支持时不设置。
SEED_THINKING=disabled
```

`SEED_MODEL` 可直接填写官方 Model ID；如另填 `SEED_ENDPOINT_ID`，调用时优先使用这个自定义部署 ID。检查命令只回报成功/错误，不输出密钥。每次规划默认最多 4096 输出 tokens；服务端记录 provider 返回的 usage。Key 有效不代表模型已开通，`ModelNotOpen` 需要在方舟开通对应模型。

真实检索：

```dotenv
DATABASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=doubao-embedding-vision-251215
EMBEDDING_DIMENSIONS=1024
```

在 Supabase 建立专用 PostgreSQL 项目后，使用服务端连接字符串（需要 SSL 时保留 `sslmode=require`）。仅运行一次 `python -m app.manage migrate-search`。不要让浏览器拿到数据库密码。搜索时为可访问结构卡写入真实 embedding，保存模型和内容 hash；相同卡片不反复生成向量。先过滤公共/个人权限，再精确 cosine Top-3；无需 ANN 索引。数据库或 embedding 不可用时界面回到手动选卡。

[官方向量化文档](https://docs.volcengine.com/docs/ark/vectorization?lang=zh)：使用 `/api/v3/embeddings/multimodal`，1024 维浮点向量。真实接通后用不同 brief 搜索，查看 `retrieval` 事件里的 card IDs，并核对故事板引用；本地 SQL 测试不能代替这一验收。

可选 Seedance：

```dotenv
SEEDANCE_ENABLED=true
SEEDANCE_PROVIDER=seedance
SEEDANCE_API_KEY=
SEEDANCE_MODEL=
SEEDANCE_GLOBAL_LIMIT=2
```

模型 ID 从控制台复制，不猜型号字符串。普通导出不调用视频 API。每次显式选择 1–2 个镜头，固定 5 秒、720p、9:16、静音。输入可以纯文本，也可以明确选择一张本人确认无真人人脸的产品参考帧。已有女性特写不作为参考输入。生成成功后素材下载至持久盘并附着新版本；失败回退目标素材，UI 显示原因。

如果 POST 响应不确定，状态保存为 `submission_unknown`，禁止自动重发。到火山控制台核查请求和计费后再处理；不要通过反复变更 prompt 绕过这个保护。若已知 request ID，重试继续 GET 轮询。成功缓存复用不重复扣视频额度。

明确的 400/401/403/404/422 拒绝保存为 `rejected`，只记录安全的错误码；修复后可显式重试，仍经过额度检查。超时、连接中断和 5xx 不视为明确拒绝。

[官方视频接口](https://docs.volcengine.com/docs/ark/create-video-generation-task-api?lang=zh&redirect=1)。Mock client 仅复制目标素材以测试状态机，不产生新视觉内容。

## 4. API 与额度

| API | 行为 |
| --- | --- |
| `POST/GET /api/session` | 邀请兑换 / 当前额度 |
| `GET /api/workspace` | 私人资源、故事板、导出、最近 50 个任务 |
| `GET /api/library` | 公共与个人结构卡 |
| `POST /api/library/search` | 真实检索或明确的手动回退 |
| `POST /api/videos/upload` | 同步受限上传 |
| `POST /api/demo` | 将自制演示素材复制到当前工作区 |
| `GET/PATCH /api/storyboards/{id}` | 读取 / 保存新版本，旧版本编辑返回 409 |
| `POST /api/jobs` | analyze / learn / generate / assets / render，返回 202 |
| `GET /api/jobs/{id}` | 查询任务 |
| `POST /api/jobs/{id}/retry` | 重试失败任务，重新验证归属、版本和额度 |
| `GET /api/media/{id}` | 授权访问素材、帧或 MP4；`?download=true` 下载 |
| `POST /api/audio/upload` | 可选 MP3/WAV/M4A，≤10 MB |
| `POST /api/feedback` | 愿意发布 / 修改后发布 / 暂不使用及原因 |

默认 3 次草稿生成/邀请，全站 10 次；生成和失败重试均扣额度。学习卡与草稿共享额外 planner 上限：个人额度×3，全站×3。每会话最多 3 个活动任务；渲染次数最多额度×4。分析、上传、搜索、音轨、反馈也有独立次数限制。视频全站最多 2 次新提交；每会话最多 2 次。

调整上限使用环境变量并重启。`python -m app.manage reset-limits` 会清空计数器（所有用户），只应在结束测试、没有运行任务时由管理员执行。它不会删除邀请码、任务或素材，不用于给单个访客无限续额度。`python -m app.manage events` 可查看最近事件与模型 usage。

## 5. 故障与旧数据

401：邀请码/会话过期或模型认证失败，UI 会区分。429：配额或 provider 限流。409：编辑版本过时，重新载入草稿。模型、检索、渲染失败都保留已经保存的资源。失败任务重试会再校验当前版本，不偷偷渲染旧草稿。

旧同步入口仅在 `LEGACY_LOCAL_API=true` 且开发环境、loopback 客户端可用；生产启动时禁止。没有 `/static` 整库挂载。老 JSON 可用 renderer CLI 指定单个 storyboard 和仅含其所需素材的 public-dir 在本地渲染；CLI 返回的文件路径为本地结果，不是公共下载链接。

## 6. 面试演示

先打开首页第一条“真实 AI 链路”样片：它使用真实向量检索、Seed 文本规划和一个 Seedance 开场镜头，后两段使用自制演示素材。其余两条是 mock 规划 + 真分析/真渲染的备份样片。生成一个中文咖啡 brief，展示结构卡来源，修改开场字幕和时长，保存 v2，导出并刷新浏览器，等待成功后下载。

说明已实现的取舍：分离结构与画面；JSON 可审计和编辑；后台任务防重复；每个导出绑定版本；成本通过可选模型、次数和并发控制。真实模型、云端地址、真实使用意愿数据尚未验收时，应如实说明，不声称已上线或已有用户。

## 7. 仅本地运行与真实集成检查

不需要 Render、Supabase 或控制用户的 Chrome。可以复用本项目的 pgvector 容器（主机端口 55432），Remotion 使用自己的 Chromium。

```bash
docker compose --profile search up -d search
PYTHONPATH=apps/api apps/api/.venv/bin/python -m app.manage migrate-search
PYTHONPATH=apps/api apps/api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

`.env` 的 `DATABASE_URL` 使用本项目 Compose 定义的本地数据库与 `127.0.0.1:55432`，不要连接其他项目的数据库。前端已有静态导出时直接打开 `http://localhost:8000`；前端变更后先运行 `npm run build:web`。管理命令 `invite` 生成一次性邀请码。

真实集成检查会调用收费接口，需显式启用。先停止使用同一 DATA_DIR 的 API 服务，依次执行：

```bash
apps/api/.venv/bin/python scripts/verify_live.py draft --allow-paid
apps/api/.venv/bin/python scripts/verify_live.py assets --allow-paid
apps/api/.venv/bin/python scripts/verify_live.py render --allow-paid
```

`draft` 为三张人工公共卡和两个测试 brief 生成真实向量、执行 SQL 检索、生成一个真实故事板；`assets` 只增强第一个场景；`render` 验证生成资产已经附着后导出 MP4。结果保存到 `data/integration/local-live-2026-09-30/report.json`。`session.json` 是 0600 权限的私人会话状态，不要分享。完成阶段会复用，不自动重发收费请求。失败任务可显式使用 `--retry-failed`；已完成但无资产的任务可用 `--resume-assets` 重新检查，provider 层仍保护未知提交和已知任务 ID。

## 8. 真实链路验收记录（2026-09-30）

在本机完成以下实际调用，不代表云端上线或用户采用：

- 文本规划：`doubao-seed-2-1-lite-260915`，3874 tokens（输入 3151、输出 723），生成 3 场景、15 秒故事板。关闭 thinking；公开 Model ID 可直接调用，不强制要求 endpoint ID。
- 检索：`doubao-embedding-vision-251215` 文本输入、1024 维。为三张人工结构卡建立真实向量，用两个 brief 执行本地 pgvector SQL 查询，两次第一名不同；故事板场景引用实际命中的卡片。此小样本验证不能证明检索质量。
- 视频：`doubao-seedance-2-5-260628`，纯文本生成一个无人物产品镜头，实际时长约 5.04 秒，usage 为 108900 tokens。此前一次提交未拿到 ID；两次官方任务列表查询确认没有任务后才显式重试。没有盲目重发；两次本地额度预留仍计入全站上限，不自动清零。
- 成片：故事板 `44ae1b40-532c-4a56-bf49-3587d02a2275` v2；720×1280、30fps、450 帧（视频轨 15 秒，容器含音频尾部约 15.061 秒）。Remotion 渲染约 36.8 秒；已解码 2、7、12、14.9 秒画面，并检查中文字幕和真实生成开场。字幕样式仍较大，后两段是简化动画素材，画风尚未统一。
- 入口：首页 `/examples/live.mp4`；原始输出保存在独立 render 目录，没有覆盖旧成片。详细 ID、模型 usage 与文件路径记录在本地 `data/integration/local-live-2026-09-30/report.json`。
- 本地检查：16 个 Python 测试通过（包含专用 PostgreSQL 的 SQL 测试），Web / renderer / schemas 类型检查和 Next 静态构建通过。

[官方模型价格](https://docs.volcengine.com/docs/ark/model-pricing?lang=zh)按视频 70 元/百万 tokens 估算，本次成功视频任务约人民币 7.62 元；文本、embedding 另计，免费额度和实际账单以控制台为准。应用额度不是账单封顶。

示例是虚构 Craft 咖啡广告。没有真实客户、投放、留存、收入或节省工时数据。原有面试素材库中的“真实接口未验证”属于此前调查时点，应结合本节更新陈述；不能据此改变历史开发时间线或个人贡献结论。
