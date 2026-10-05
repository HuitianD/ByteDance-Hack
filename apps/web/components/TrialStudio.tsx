"use client";
import { useCallback, useEffect, useState } from "react";
import { useLanguage } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import {
  ReferenceEvidenceDetails,
  referenceOriginLabel,
} from "@/components/ReferenceEvidenceDetails";
import {
  trial,
  mediaUrl,
  type Workspace,
  type Session,
  type Capabilities,
  type JobSubmission,
} from "@/lib/trial-api";
import type { Storyboard, StructureCard } from "@/lib/types";

const empty: Workspace = {
  uploads: [],
  storyboards: [],
  renders: [],
  jobs: [],
  audio: [],
};
const layouts = [
  "hook_title",
  "text_over_media",
  "feature_card",
  "split_compare",
  "cta_card",
  "default_scene",
];
const animations = [
  "none",
  "fade-in",
  "slide-up",
  "scale-pulse",
  "ken-burns",
  "type-on",
];
const transitions = ["none", "cut", "fade", "slide"];

export function TrialStudio() {
  const { locale } = useLanguage();
  const zh = locale === "zh";
  const t = (en: string, cn: string) => (zh ? cn : en);
  const [session, setSession] = useState<Session | null>(null),
    [ws, setWs] = useState(empty),
    [cards, setCards] = useState<StructureCard[]>([]),
    [caps, setCaps] = useState<Capabilities | null>(null);
  const [code, setCode] = useState(""),
    [error, setError] = useState(""),
    [note, setNote] = useState(""),
    [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string[]>([]),
    [target, setTarget] = useState(""),
    [prompt, setPrompt] = useState(""),
    [duration, setDuration] = useState(20);
  const [draft, setDraft] = useState<Storyboard | null>(null),
    [dirty, setDirty] = useState(false),
    [searchMode, setSearchMode] = useState("manual");
  const [hero, setHero] = useState<string[]>([]),
    [referenceFrame, setReferenceFrame] = useState(""),
    [noFaces, setNoFaces] = useState(false);
  const [feedback, setFeedback] = useState(""),
    [rating, setRating] = useState("edit");
  const refresh = useCallback(async () => {
    const [w, s] = await Promise.all([trial.workspace(), trial.session()]);
    setWs(w);
    setSession(s);
    return w;
  }, []);
  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const [lib, status] = await Promise.all([
          trial.library(),
          trial.status(),
        ]);
        if (!active) return;
        setCards(lib.cards);
        setCaps(status);
        try {
          const w = await refresh();
          if (!active) return;
          const saved = localStorage.getItem("viralcraft-draft");
          const b =
            w.storyboards.find((x) => x.id === saved) || w.storyboards[0];
          if (b) {
            setDraft(b);
            setTarget(b.target_media_job_id || "");
            setSelected(b.source_structure_card_ids);
            setPrompt(b.user_prompt);
            setDuration(b.target_duration_seconds);
          } else if (w.uploads[0]) setTarget(w.uploads[0].id);
        } catch (e) {
          if (!(e instanceof ApiError && e.status === 401)) throw e;
        }
      } catch (e) {
        if (active) setError(String(e));
      }
    })();
    return () => {
      active = false;
    };
  }, [refresh]);
  const pending = ws.jobs.some(
    (j) => j.status === "queued" || j.status === "running",
  );
  useEffect(() => {
    if (!session || !pending) return;
    const timer = setInterval(() => {
      refresh().catch((e) => setError(String(e)));
    }, 2000);
    return () => clearInterval(timer);
  }, [session, pending, refresh]);
  useEffect(() => {
    if (!draft) {
      if (ws.storyboards[0]) setDraft(ws.storyboards[0]);
      return;
    }
    localStorage.setItem("viralcraft-draft", draft.id);
    const newest = ws.storyboards.find((b) => b.id === draft.id);
    if (newest && !dirty && (newest.version || 1) > (draft.version || 1))
      setDraft(newest);
  }, [draft, ws.storyboards, dirty]);
  async function action(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    setNote("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }
  async function submit(body: JobSubmission) {
    const job = await trial.submit(body);
    await refresh();
    setNote(
      t(
        `Task ${job.status}. You can refresh this page safely.`,
        `任务已${job.status === "queued" ? "排队" : "开始"}，刷新页面也可恢复。`,
      ),
    );
  }
  function editScene(index: number, key: string, value: string | number) {
    if (!draft) return;
    setDraft({
      ...draft,
      scenes: draft.scenes.map((s, i) =>
        i === index ? { ...s, [key]: value } : s,
      ),
    });
    setDirty(true);
  }
  const upload = ws.uploads.find((u) => u.id === target);
  const results = ws.renders.filter((r) => r.storyboard_id === draft?.id);
  const disabled = busy || !session;
  return (
    <div className="space-y-8">
      <div className="grid gap-4 sm:grid-cols-3">
        {[
          ["01", t("Reference & footage", "参考与素材")],
          ["02", t("Edit your draft", "修改草稿")],
          ["03", t("Export a video", "导出成片")],
        ].map(([n, label]) => (
          <div key={n} className="rounded-xl border border-neutral-800 p-4">
            <span className="text-fuchsia-300">{n}</span>
            <p className="mt-1 font-medium">{label}</p>
          </div>
        ))}
      </div>
      {!session ? (
        <section className="studio-panel">
          <h2>{t("Try ViralCraft", "试用 ViralCraft")}</h2>
          <p>
            {t(
              "Explore the reference patterns below. An invitation unlocks uploads and generation.",
              "可直接浏览下方结构模板，邀请码可解锁上传和生成。",
            )}
          </p>
          <form
            className="mt-4 flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              action(async () => {
                setSession(await trial.login(code.trim()));
                setCode("");
                await refresh();
              });
            }}
          >
            <input
              aria-label={t("Invitation code", "邀请码")}
              className="studio-input min-w-0 flex-1"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={t("Invitation code", "输入邀请码")}
              autoComplete="off"
            />
            <button className="studio-button" disabled={busy || !code.trim()}>
              {t("Start trial", "开始试用")}
            </button>
          </form>
        </section>
      ) : (
        <div className="flex flex-wrap justify-between gap-2 text-sm text-neutral-400">
          <span>{t("Private trial workspace", "私人试用工作区")}</span>
          <span>
            {Math.max(0, session.quota - (session.used.generate || 0))}{" "}
            {t("draft generations remaining", "次草稿生成剩余额度")}
          </span>
        </div>
      )}
      {caps?.planner.provider === "mock" && (
        <p className="studio-notice">
          {t(
            "Demo mode: deterministic sample planning, not a live AI response. Upload analysis and video rendering are real.",
            "演示模式：草稿使用确定性示例逻辑，不是真实 AI 响应；素材分析与视频渲染是真实执行。",
          )}
        </p>
      )}
      {caps && !caps.planner.configured && (
        <p className="studio-notice">
          {t(
            "The planning model is not configured. You can browse examples while configuration is completed.",
            "规划模型尚未配置，可先浏览示例。",
          )}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-200"
        >
          {error}
        </p>
      )}
      {note && (
        <p role="status" className="studio-notice">
          {note}
        </p>
      )}
      <section className="studio-panel">
        <h2>
          {t(
            "1. Pick a structure and bring your footage",
            "1. 选择结构，准备自己的素材",
          )}
        </h2>
        <p>
          {t(
            "Patterns guide the story. Your target video supplies the actual pictures.",
            "结构决定讲述方式，目标素材决定最终画面。",
          )}
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {cards.map((c) => (
            <article
              key={c.id}
              className={`min-w-0 rounded-xl border p-4 ${selected.includes(c.id) ? "border-fuchsia-400 bg-fuchsia-500/10" : "border-neutral-800"}`}
            >
              <label className="flex cursor-pointer items-start gap-2">
                <input
                  className="mt-1"
                  type="checkbox"
                  checked={selected.includes(c.id)}
                  disabled={
                    busy || (!selected.includes(c.id) && selected.length >= 3)
                  }
                  onChange={() =>
                    setSelected((s) =>
                      s.includes(c.id)
                        ? s.filter((x) => x !== c.id)
                        : [...s, c.id],
                    )
                  }
                />
                <span className="font-medium">{c.pattern_name}</span>
              </label>
              <p className="mt-2 text-xs">{c.summary}</p>
              <div className="mt-3 text-xs text-fuchsia-300">
                {c.editing_atoms.map((a) => a.kind).join(" → ")}
              </div>
              <p className="mt-2 text-xs">{referenceOriginLabel(c, zh)}</p>
              <ReferenceEvidenceDetails card={c} />
            </article>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap items-center gap-3">
          <button
            className="studio-secondary"
            disabled={disabled}
            onClick={() =>
              action(async () => {
                const u = await trial.demo();
                setTarget(u.id);
                await refresh();
              })
            }
          >
            {t("Use demo footage", "使用示例素材")}
          </button>
          <label className={`studio-secondary ${disabled ? "opacity-40" : ""}`}>
            {t("Upload target video", "上传目标视频")}
            <input
              className="sr-only"
              type="file"
              accept="video/*"
              disabled={disabled}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f)
                  action(async () => {
                    const u = await trial.upload(f);
                    setTarget(u.id);
                    await refresh();
                  });
                e.target.value = "";
              }}
            />
          </label>
          <span className="text-xs text-neutral-500">
            {t("Up to 30 seconds / 30 MB", "最多 30 秒 / 30 MB")}
          </span>
        </div>
        {ws.uploads.length > 0 && (
          <label className="mt-4 block text-sm">
            {t("Target footage", "目标素材")}
            <select
              className="studio-input mt-2 w-full"
              value={target}
              onChange={(e) => {
                setTarget(e.target.value);
                setReferenceFrame("");
              }}
            >
              {ws.uploads.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.original_filename}
                </option>
              ))}
            </select>
          </label>
        )}
        {upload && (
          <details className="mt-4 text-sm">
            <summary className="cursor-pointer text-neutral-400">
              {t(
                "Preview and learn from this video",
                "预览并从这条视频提取结构",
              )}
            </summary>
            <video
              className="mt-3 max-h-64 rounded-lg"
              src={mediaUrl(upload.url)}
              controls
            />
            <div className="mt-3 flex gap-2">
              <button
                className="studio-secondary"
                disabled={disabled || pending}
                onClick={() =>
                  action(() =>
                    submit({ kind: "analyze", resource_id: upload.id }),
                  )
                }
              >
                {t("Analyze footage", "分析素材")}
              </button>
              <button
                className="studio-secondary"
                disabled={disabled || pending}
                onClick={() =>
                  action(() =>
                    submit({ kind: "learn", resource_id: upload.id }),
                  )
                }
              >
                {t("Extract reference card", "提取参考卡")}
              </button>
              <button
                className="studio-secondary"
                disabled={disabled}
                onClick={() =>
                  action(async () => setCards((await trial.library()).cards))
                }
              >
                {t("Refresh library", "刷新结构库")}
              </button>
            </div>
            <p className="mt-3 text-xs">
              {t(
                "Basic analysis detects scene boundaries and timing. Reference-card extraction separately analyzes keyframes; review the results before reuse.",
                "基础分析检测分镜与时长；提取参考卡会另行分析关键帧，结果需核对。",
              )}
            </p>
            {upload.analysis && (
              <p className="mt-2 text-xs">
                {upload.analysis.scenes.length} {t("scenes", "个场景")} ·{" "}
                {upload.analysis.scene_detection_method}
              </p>
            )}
          </details>
        )}
        <label className="mt-5 block text-sm">
          {t("Your campaign brief", "你的创作要求")}
          <textarea
            className="studio-input mt-2 w-full"
            rows={4}
            maxLength={2000}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t(
              "Introduce our coffee shop. Warm, calm tone. Mention freshly roasted beans. CTA: Visit us this weekend.",
              "介绍我们的咖啡店，温暖平静的风格，突出新鲜烘焙，结尾邀请周末到店。",
            )}
          />
        </label>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <select
            aria-label={t("Video duration", "视频时长")}
            className="studio-input"
            value={duration}
            onChange={(e) => setDuration(Number(e.target.value))}
          >
            <option value={15}>15s</option>
            <option value={20}>20s</option>
          </select>
          <button
            className="studio-secondary"
            disabled={disabled || !prompt.trim()}
            onClick={() =>
              action(async () => {
                const r = await trial.search(prompt);
                setCards(r.cards);
                setSelected(r.cards.slice(0, 3).map((c) => c.id));
                setSearchMode(r.mode);
                if (r.message) setNote(r.message);
              })
            }
          >
            {t("Find matching patterns", "查找匹配结构")}
          </button>
          <span className="text-xs text-neutral-500">
            {searchMode === "semantic"
              ? t("Semantic Top-3", "语义检索 Top-3")
              : t("Manual selection", "手动选卡")}
          </span>
          <button
            className="studio-button"
            disabled={
              disabled ||
              pending ||
              !target ||
              !selected.length ||
              !prompt.trim() ||
              !caps?.planner.configured
            }
            onClick={() =>
              action(() =>
                submit({
                  kind: "generate",
                  storyboard: {
                    user_prompt: prompt,
                    target_duration_seconds: duration,
                    reference_card_ids: selected,
                    target_media_job_id: target,
                  },
                }),
              )
            }
          >
            {t("Create a draft", "生成草稿")}
          </button>
        </div>
      </section>
      {ws.jobs.length > 0 && (
        <section className="studio-panel">
          <h2>{t("Activity", "任务进度")}</h2>
          <div className="mt-3 space-y-3">
            {ws.jobs.slice(0, 6).map((j) => (
              <div
                key={j.id}
                className="rounded-lg border border-neutral-800 p-3 text-sm"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span>
                    {t(
                      j.kind,
                      (
                        {
                          analyze: "分析素材",
                          learn: "提取结构",
                          generate: "规划草稿",
                          render: "渲染视频",
                          assets: "生成镜头",
                        } as Record<string, string>
                      )[j.kind] || j.kind,
                    )}{" "}
                    ·{" "}
                    {t(
                      j.status,
                      (
                        {
                          queued: "排队中",
                          running: "处理中",
                          succeeded: "已完成",
                          failed: "失败",
                          cancelled: "已取消",
                        } as Record<string, string>
                      )[j.status] || j.status,
                    )}
                  </span>
                  {j.kind === "generate" && j.status === "succeeded" && (
                    <button
                      className="text-fuchsia-300"
                      onClick={() => {
                        const b = ws.storyboards.find(
                          (x) => x.id === j.result?.id,
                        );
                        if (b) {
                          setDraft(b);
                          setDirty(false);
                          setHero([]);
                        }
                      }}
                    >
                      {t("Open draft", "打开草稿")}
                    </button>
                  )}
                </div>
                {j.error && <p className="mt-2 text-red-300">{j.error}</p>}
                {j.status === "failed" && (
                  <button
                    className="text-fuchsia-300 mt-2"
                    disabled={disabled}
                    onClick={() =>
                      action(async () => {
                        await trial.retry(j.id);
                        await refresh();
                      })
                    }
                  >
                    {t("Retry · trial limits apply", "重试 · 计入试用额度")}
                  </button>
                )}
                {!!j.result?.warnings && (
                  <p className="mt-2 text-amber-300">
                    {String(j.result.warnings)}
                  </p>
                )}
                <p className="mt-1 text-xs text-neutral-500">
                  {new Date(j.created_at * 1000).toLocaleTimeString()}{" "}
                  {j.status === "queued"
                    ? t("· Waiting for the renderer", "· 等待前面的任务")
                    : ""}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}
      {ws.storyboards.length > 0 && (
        <section className="studio-panel">
          <h2>{t("2. Make the draft yours", "2. 修改你的草稿")}</h2>
          <select
            aria-label={t("Saved drafts", "已保存草稿")}
            className="studio-input mt-3 w-full"
            value={draft?.id || ""}
            onChange={(e) => {
              setDraft(
                ws.storyboards.find((b) => b.id === e.target.value) || null,
              );
              setDirty(false);
              setHero([]);
            }}
          >
            <option value="" disabled>
              {t("Choose a draft", "选择草稿")}
            </option>
            {ws.storyboards.map((b) => (
              <option key={b.id} value={b.id}>
                {b.title} · v{b.version}
              </option>
            ))}
          </select>
          {draft && (
            <>
              <label className="mt-4 block text-sm">
                {t("Title", "标题")}
                <input
                  className="studio-input mt-2 w-full"
                  value={draft.title}
                  onChange={(e) => {
                    setDraft({ ...draft, title: e.target.value });
                    setDirty(true);
                  }}
                />
              </label>
              <p className="mt-3 text-sm text-neutral-400">
                v{draft.version} ·{" "}
                {draft.scenes
                  .reduce((a, s) => a + s.duration_seconds, 0)
                  .toFixed(1)}
                s ·{" "}
                {dirty
                  ? t("Unsaved edits", "有未保存修改")
                  : t("Saved", "已保存")}
                {draft.generation_mode === "mock" ? " · MOCK" : ""}
              </p>
              <div className="mt-4 space-y-4">
                {draft.scenes.map((s, i) => (
                  <div
                    key={s.scene_id}
                    className="rounded-xl border border-neutral-800 p-4"
                  >
                    <div className="mb-3 flex justify-between gap-2">
                      <span className="text-sm text-fuchsia-300">
                        {i + 1}. {s.source_editing_atoms.join(" + ")}
                      </span>
                      {s.generated_asset_id && (
                        <span className="text-xs text-emerald-300">
                          {t("Generated clip attached", "已使用生成镜头")}
                        </span>
                      )}
                    </div>
                    <label className="block text-xs text-neutral-400">
                      {t("On-screen caption", "画面字幕")}
                      <textarea
                        aria-label={`${t("Scene", "场景")} ${i + 1} ${t("caption", "字幕")}`}
                        className="studio-input mt-1 w-full"
                        rows={2}
                        maxLength={240}
                        value={s.text || ""}
                        onChange={(e) => editScene(i, "text", e.target.value)}
                      />
                    </label>
                    <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <label className="text-xs">
                        {t("Seconds", "秒")}
                        <input
                          className="studio-input mt-1 w-full"
                          type="number"
                          min={0.5}
                          max={20}
                          step={0.1}
                          value={s.duration_seconds}
                          onChange={(e) =>
                            editScene(
                              i,
                              "duration_seconds",
                              Number(e.target.value),
                            )
                          }
                        />
                      </label>
                      {[
                        ["layout", layouts],
                        ["animation", animations],
                        ["transition", transitions],
                      ].map(([key, values]) => (
                        <label key={String(key)} className="text-xs">
                          {String(key)}
                          <select
                            className="studio-input mt-1 w-full"
                            value={String(s[key as keyof typeof s] || "none")}
                            onChange={(e) =>
                              editScene(i, String(key), e.target.value)
                            }
                          >
                            {(values as string[]).map((v) => (
                              <option key={v}>{v}</option>
                            ))}
                          </select>
                        </label>
                      ))}
                    </div>
                    <p className="mt-3 break-all text-xs text-neutral-500">
                      {t("Reference", "参考")}:{" "}
                      {cards.find((c) => c.id === s.source_structure_card_id)
                        ?.pattern_name || s.source_structure_card_id}
                    </p>
                  </div>
                ))}
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  className="studio-button"
                  disabled={disabled || !dirty}
                  onClick={() =>
                    action(async () => {
                      setDraft(await trial.edit(draft));
                      setDirty(false);
                      await refresh();
                      setNote(
                        t(
                          "Saved. Export again to see these changes.",
                          "已保存，重新导出后可看到修改。",
                        ),
                      );
                    })
                  }
                >
                  {t("Save changes", "保存修改")}
                </button>
                <button
                  className="studio-secondary"
                  disabled={!dirty || busy}
                  onClick={() => {
                    setDraft(
                      ws.storyboards.find((b) => b.id === draft.id) || draft,
                    );
                    setDirty(false);
                  }}
                >
                  {t("Discard edits", "放弃修改")}
                </button>
              </div>
            </>
          )}
        </section>
      )}
      {draft && (
        <section className="studio-panel">
          <h2>{t("3. Export your video", "3. 导出视频")}</h2>
          <p>
            {t(
              "Exports use the saved draft. Earlier exports are kept.",
              "导出使用已保存版本，之前的成片会保留。",
            )}
          </p>
          <label className="mt-4 block text-sm">
            {t("Background audio (optional)", "背景音轨（可选）")}
            <select
              className="studio-input mt-2 w-full"
              value={draft.audio_asset_id || ""}
              onChange={(e) => {
                setDraft({ ...draft, audio_asset_id: e.target.value || null });
                setDirty(true);
              }}
            >
              <option value="">{t("Silent", "静音")}</option>
              {ws.audio.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </label>
          <label className="studio-secondary mt-3 inline-block">
            {t("Upload your audio", "上传你的音轨")}
            <input
              className="sr-only"
              type="file"
              accept="audio/*"
              disabled={disabled}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f)
                  action(async () => {
                    await trial.upload(f, true);
                    await refresh();
                  });
                e.target.value = "";
              }}
            />
          </label>
          {caps?.video.enabled && (
            <details className="mt-5 rounded-xl border border-fuchsia-500/20 p-4">
              <summary>
                {t("Optional: generate a hero shot", "可选：生成一个重点镜头")}
              </summary>
              <p className="mt-2 text-xs">
                {t(
                  "Uses separate video generation credits. Choose up to two scenes. Failed generation keeps your original footage.",
                  "使用单独的视频生成额度，最多选择两个场景，失败仍可使用原素材导出。",
                )}
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                {draft.scenes.map((s, i) => (
                  <label key={s.scene_id} className="text-sm">
                    <input
                      type="checkbox"
                      checked={hero.includes(s.scene_id)}
                      disabled={!hero.includes(s.scene_id) && hero.length >= 2}
                      onChange={() =>
                        setHero((h) =>
                          h.includes(s.scene_id)
                            ? h.filter((x) => x !== s.scene_id)
                            : [...h, s.scene_id],
                        )
                      }
                    />{" "}
                    {t("Scene", "场景")} {i + 1}
                  </label>
                ))}
              </div>
              <select
                aria-label={t("Reference frame", "参考帧")}
                className="studio-input mt-3 w-full"
                value={referenceFrame}
                onChange={(e) => {
                  setReferenceFrame(e.target.value);
                  setNoFaces(false);
                }}
              >
                <option value="">{t("Text only", "仅文字生成")}</option>
                {ws.uploads
                  .find((u) => u.id === draft.target_media_job_id)
                  ?.frames?.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.timestamp_seconds}s
                    </option>
                  ))}
              </select>
              {referenceFrame && (
                <>
                  <img
                    className="mt-3 max-h-40 rounded"
                    src={mediaUrl(`/api/media/${referenceFrame}`)}
                    alt={t("Selected product reference", "选择的产品参考帧")}
                  />
                  <label className="mt-3 block text-xs">
                    <input
                      type="checkbox"
                      checked={noFaces}
                      onChange={(e) => setNoFaces(e.target.checked)}
                    />{" "}
                    {t(
                      "This product frame contains no real faces.",
                      "这张产品参考帧不含真人人脸。",
                    )}
                  </label>
                </>
              )}
              <button
                className="studio-secondary mt-3"
                disabled={
                  disabled ||
                  pending ||
                  dirty ||
                  !hero.length ||
                  !caps.video.configured ||
                  (!!referenceFrame && !noFaces)
                }
                onClick={() =>
                  action(() =>
                    submit({
                      kind: "assets",
                      resource_id: draft.id,
                      version: draft.version,
                      scene_ids: hero,
                      ...(referenceFrame
                        ? {
                            reference_frame_id: referenceFrame,
                            reference_has_no_faces: noFaces,
                          }
                        : {}),
                    }),
                  )
                }
              >
                {t("Generate selected clips", "生成选中镜头")}
              </button>
            </details>
          )}
          <button
            className="studio-button mt-5"
            disabled={disabled || pending || dirty}
            onClick={() =>
              action(() =>
                submit({
                  kind: "render",
                  resource_id: draft.id,
                  version: draft.version,
                }),
              )
            }
          >
            {t("Export saved draft", "导出已保存草稿")}
          </button>
          {dirty && (
            <p className="mt-2 text-sm text-amber-300">
              {t("Save your edits before exporting.", "请先保存修改再导出。")}
            </p>
          )}
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            {results.map((r) => (
              <div
                key={r.id}
                className="rounded-xl border border-neutral-800 p-3"
              >
                <p className="mb-2 text-xs text-neutral-400">
                  v{r.version} · {((r.duration_ms || 0) / 1000).toFixed(1)}s{" "}
                  {t("render time", "渲染耗时")}
                </p>
                <video
                  className="mx-auto max-h-96 rounded"
                  controls
                  playsInline
                  preload="metadata"
                  src={mediaUrl(`/api/media/${r.id}`)}
                />
                <a
                  className="studio-secondary mt-3 inline-block"
                  href={mediaUrl(`/api/media/${r.id}?download=true`)}
                >
                  {t("Download MP4", "下载 MP4")}
                </a>
              </div>
            ))}
          </div>
          {results.length > 0 && (
            <form
              className="mt-6 border-t border-neutral-800 pt-4"
              onSubmit={(e) => {
                e.preventDefault();
                action(async () => {
                  await trial.feedback(draft.id, rating, feedback);
                  setNote(
                    t("Feedback saved. Thank you.", "反馈已保存，谢谢。"),
                  );
                });
              }}
            >
              <label className="text-sm">
                {t("Would you use this video?", "你会使用这条视频吗？")}
                <select
                  className="studio-input mt-2 w-full"
                  value={rating}
                  onChange={(e) => setRating(e.target.value)}
                >
                  <option value="publish">
                    {t("Ready to publish", "可以直接发布")}
                  </option>
                  <option value="edit">
                    {t("After small edits", "稍作修改后发布")}
                  </option>
                  <option value="reject">
                    {t("Not yet useful", "暂时不会使用")}
                  </option>
                </select>
              </label>
              <textarea
                className="studio-input mt-2 w-full"
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                maxLength={1000}
                placeholder={t(
                  "What would make it more useful?",
                  "哪一点最需要改进？",
                )}
              />
              <button className="studio-secondary mt-2" disabled={busy}>
                {t("Send feedback", "提交反馈")}
              </button>
            </form>
          )}
        </section>
      )}
    </div>
  );
}
