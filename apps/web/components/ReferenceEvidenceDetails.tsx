"use client";

import { useRef, useState } from "react";
import type { StructureAspect } from "@viralcraft/schemas";
import { useLanguage } from "@/lib/i18n";
import { mediaUrl } from "@/lib/trial-api";
import type { StructureCard } from "@/lib/types";

/** Reference media must stay on an explicitly supported local route. */
function referenceMediaUrl(value?: string | null): string | undefined {
  if (
    !value ||
    value.includes("..") ||
    !/^\/(?:api\/media\/[a-zA-Z0-9_-]+|references\/[a-zA-Z0-9_./-]+)$/.test(
      value,
    )
  ) {
    return undefined;
  }
  return mediaUrl(value);
}

function sourceLink(value?: string | null): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

function time(seconds: number): string {
  const safe = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;
  return `${Math.floor(safe / 60)}:${(safe % 60).toFixed(1).padStart(4, "0")}`;
}

export function referenceOriginLabel(card: StructureCard, zh: boolean): string {
  if (card.origin === "curated") return zh ? "预置模板" : "Preset template";
  if (card.origin === "mock" || card.analysis?.mode === "mock")
    return zh ? "Mock 提取" : "Mock extraction";
  if (card.origin === "vision_llm" || card.analysis?.mode === "vision")
    return zh ? "样例视觉提取" : "Extracted from reference frames";
  if (card.analysis?.mode === "metadata" || card.origin === "seed")
    return zh ? "基于元信息提取" : "Metadata-based extraction";
  return zh ? "历史结构卡" : "Historical structure card";
}

export function ReferenceEvidenceDetails({ card }: { card: StructureCard }) {
  const { locale } = useLanguage();
  const zh = locale === "zh";
  const t = (en: string, cn: string) => (zh ? cn : en);
  const [open, setOpen] = useState(false);
  const video = useRef<HTMLVideoElement>(null);
  const pendingSeek = useRef<number | null>(null);
  const source = card.source;
  const observations = card.observations || [];
  const rules = card.rules || [];
  const src = referenceMediaUrl(source?.media_url);
  const review = card.review;
  const sourceKinds: Record<string, string> = {
    self_authored_demo: t("Self-authored demo", "原创演示样例"),
    licensed_reference: t("Licensed reference", "已记录许可的参考样例"),
    user_upload: t("User-provided reference", "用户上传样例"),
  };
  const reviewMethods: Record<string, string> = {
    assistant_visual: t("AI visual review", "AI 复核"),
    human: t("Human review", "人工复核"),
    none: t("Not reviewed", "尚未复核"),
  };
  const reviewStatuses: Record<string, string> = {
    approved: t("Approved", "已通过"),
    rejected: t("Rejected", "未通过"),
    pending: t("Pending", "待审核"),
  };
  const aspects: Record<StructureAspect, string> = {
    hook: t("Opening hook", "开场"),
    pacing: t("Pacing", "镜头节奏"),
    information_flow: t("Information flow", "信息推进"),
    caption_layout: t("Caption layout", "字幕布局"),
  };

  function seek(seconds: number) {
    const player = video.current;
    if (!player || !Number.isFinite(seconds)) return;
    if (player.readyState < 1) {
      pendingSeek.current = seconds;
      return;
    }
    player.currentTime = Math.max(
      0,
      Math.min(
        seconds,
        Number.isFinite(player.duration) ? player.duration : seconds,
      ),
    );
    void player.play().catch(() => {
      // Seeking still works if the browser requires its native play button.
    });
  }

  function timestamp(start: number, end?: number) {
    const label = `${time(start)}${end === undefined ? "" : `–${time(end)}`}`;
    return src ? (
      <button
        type="button"
        className="rounded text-left font-mono text-fuchsia-300 underline underline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-fuchsia-300"
        onClick={() => seek(start)}
        aria-label={t(`Play reference at ${label}`, `播放参考视频 ${label}`)}
      >
        {label}
      </button>
    ) : (
      <span className="font-mono text-neutral-400">{label}</span>
    );
  }

  return (
    <details
      className="mt-3 border-t border-neutral-800 pt-3 text-xs text-neutral-300"
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary className="cursor-pointer font-medium text-neutral-200">
        {source || observations.length
          ? t("View reference & evidence", "查看样例与证据")
          : t("View structure details", "查看结构说明")}
      </summary>
      {open && (
        <div className="mt-4 space-y-4 break-words">
          {source && (
            <section className="space-y-2">
              <h3 className="font-medium text-neutral-100">{source.title}</h3>
              <p className="text-neutral-400">
                {sourceKinds[source.kind] ||
                  t("Source type not recorded", "来源类型未记录")}
                {source.author && ` · ${source.author}`}
              </p>
              {src ? (
                <video
                  ref={video}
                  src={src}
                  aria-label={t(
                    `Reference: ${source.title}`,
                    `参考视频：${source.title}`,
                  )}
                  controls
                  playsInline
                  preload="metadata"
                  className="max-h-56 w-full rounded-lg bg-black"
                  onLoadedMetadata={() => {
                    if (pendingSeek.current !== null) {
                      seek(pendingSeek.current);
                      pendingSeek.current = null;
                    }
                  }}
                />
              ) : (
                <p className="text-neutral-500">
                  {t(
                    "Reference playback is unavailable.",
                    "该样例暂不可播放。",
                  )}
                </p>
              )}
              <p className="text-neutral-500">
                {t(
                  "Evidence timestamps refer to this reference clip.",
                  "下方证据时间戳对应这里播放的参考片段。",
                )}
              </p>
              {(source.excerpt_start_seconds > 0 ||
                source.excerpt_end_seconds != null) && (
                <p>
                  {t("Excerpt in original: ", "原视频截取范围：")}
                  {time(source.excerpt_start_seconds)}
                  {source.excerpt_end_seconds != null &&
                    `–${time(source.excerpt_end_seconds)}`}
                </p>
              )}
              <div className="flex flex-wrap gap-x-3 gap-y-1">
                {sourceLink(source.url) && (
                  <a
                    className="text-fuchsia-300 underline"
                    href={sourceLink(source.url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {t("Original source", "原始出处")}
                  </a>
                )}
                {sourceLink(source.license_url) ? (
                  <a
                    className="text-fuchsia-300 underline"
                    href={sourceLink(source.license_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {source.license || t("License", "许可说明")}
                  </a>
                ) : (
                  <span>
                    {source.license ||
                      t("License not recorded", "尚未记录许可")}
                  </span>
                )}
              </div>
              <TextList
                title={t("Changes to source", "对原素材的处理")}
                items={source.changes}
              />
            </section>
          )}

          {observations.length > 0 ? (
            <section>
              <h3 className="font-medium text-neutral-100">
                {t("Observed evidence", "观察证据")}
              </h3>
              <ol className="mt-2 space-y-3">
                {observations.map((observation) => (
                  <li
                    key={observation.id}
                    className="rounded border border-neutral-800 p-2"
                  >
                    <div className="flex flex-wrap justify-between gap-1">
                      <span>
                        {aspects[observation.aspect] ||
                          t("Observation", "观察")}
                      </span>
                      {timestamp(
                        observation.start_seconds,
                        observation.end_seconds,
                      )}
                    </div>
                    <p className="mt-2 leading-relaxed">
                      {observation.observation}
                    </p>
                    <div className="mt-2 grid grid-cols-2 gap-2">
                      {(card.evidence_frames || [])
                        .filter((frame) =>
                          observation.frame_indices.includes(frame.index),
                        )
                        .map((frame) => {
                          const frameSrc = referenceMediaUrl(frame.url);
                          return (
                            <figure key={frame.index}>
                              {frameSrc && (
                                <img
                                  src={frameSrc}
                                  alt={t(
                                    `Reference frame at ${time(frame.timestamp_seconds)}`,
                                    `参考画面 ${time(frame.timestamp_seconds)}`,
                                  )}
                                  loading="lazy"
                                  className="aspect-video w-full rounded bg-neutral-900 object-contain"
                                />
                              )}
                              <figcaption className="mt-1">
                                {timestamp(frame.timestamp_seconds)}
                              </figcaption>
                            </figure>
                          );
                        })}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          ) : (
            <p className="rounded bg-neutral-900 p-2 text-neutral-400">
              {card.origin === "curated"
                ? t(
                    "This is a preset template, not a structure learned from a reference video.",
                    "这是预置模板，不是从参考视频中学习得到的结构。",
                  )
                : t(
                    "This card has no timestamped visual evidence.",
                    "这张卡尚无带时间戳的画面观察证据。",
                  )}
            </p>
          )}

          {rules.length > 0 ? (
            <section>
              <h3 className="font-medium text-neutral-100">
                {t("Reusable rules", "可迁移规则")}
              </h3>
              <ol className="mt-2 space-y-3">
                {rules.map((rule) => (
                  <li key={rule.id}>
                    <p className="leading-relaxed">{rule.instruction}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-neutral-500">
                      <span>{t("Evidence:", "依据：")}</span>
                      {rule.evidence_ids.map((id) => {
                        const evidence = observations.find(
                          (item) => item.id === id,
                        );
                        return evidence ? (
                          <span key={id}>
                            {timestamp(
                              evidence.start_seconds,
                              evidence.end_seconds,
                            )}
                          </span>
                        ) : (
                          <span key={id}>
                            {t("Evidence unavailable", "依据暂不可用")}
                          </span>
                        );
                      })}
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          ) : (
            <TextList
              title={t("Reusable guidance", "复用建议")}
              items={card.reusable_rules}
            />
          )}
          <TextList
            title={t("Suitable for", "适用场景")}
            items={card.applicability}
          />
          <TextList
            title={t("Footage needed", "所需素材")}
            items={card.material_requirements}
          />
          <TextList
            title={t("Limitations", "适用边界")}
            items={card.limitations}
          />

          <section className="space-y-2 border-t border-neutral-800 pt-3 text-neutral-400">
            <p>
              {t("Card version", "卡片版本")} {card.version ?? 1}
              {card.schema_version != null &&
                ` · Schema ${card.schema_version}`}
            </p>
            {review && (
              <>
                <p>
                  {reviewMethods[review.method] ||
                    t("Review method not recorded", "复核方式未记录")}
                  {" · "}
                  {reviewStatuses[review.status] ||
                    t("Status not recorded", "状态未记录")}
                </p>
                {review.notes && <p>{review.notes}</p>}
                {review.reviewed_at && (
                  <p>
                    {t("Reviewed: ", "复核时间：")}
                    {review.reviewed_at}
                  </p>
                )}
              </>
            )}
            {card.analysis && (
              <p>
                {card.analysis.mode === "vision"
                  ? t("Frame-based analysis", "关键帧分析")
                  : card.analysis.mode === "mock"
                    ? t("Mock analysis", "Mock 分析")
                    : t("Metadata analysis", "元信息分析")}
                {` · ${card.analysis.frame_count} `}
                {t("frames", "帧")}
                {card.analysis.model && ` · ${card.analysis.model}`}
                {` · ${card.analysis.prompt_version}`}
              </p>
            )}
            <p>
              {t(
                "These observations do not establish advertising performance.",
                "这些观察不能证明广告效果或爆款表现。",
              )}
            </p>
          </section>
        </div>
      )}
    </details>
  );
}

function TextList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <section>
      <h3 className="font-medium text-neutral-100">{title}</h3>
      <ul className="mt-1 list-disc space-y-1 pl-4 leading-relaxed">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </section>
  );
}
