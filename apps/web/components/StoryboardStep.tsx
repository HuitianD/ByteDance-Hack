"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import type { Storyboard, StoryboardScene } from "@/lib/types";

type Props = {
  jobId: string;
  onGenerated?: (storyboard: Storyboard) => void;
};

const DEFAULT_DURATION = 20;

export function StoryboardStep({ jobId, onGenerated }: Props) {
  const { t } = useLanguage();
  const [prompt, setPrompt] = useState("");
  const [duration, setDuration] = useState<number>(DEFAULT_DURATION);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) {
      setError(t.storyboard.promptRequired);
      return;
    }
    setBusy(true);
    setError(null);
    setStoryboard(null);
    try {
      const r = await api.generateStoryboard({
        user_prompt: prompt.trim(),
        target_duration_seconds: duration,
        source_job_ids: [jobId],
      });
      setStoryboard(r);
      onGenerated?.(r);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(t.storyboard.failedStatus(err.status, err.message));
      } else if (err instanceof Error) {
        setError(t.storyboard.failedMessage(err.message));
      } else {
        setError(t.storyboard.failedGeneric);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="storyboard-heading"
      className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
    >
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 ring-1 ring-fuchsia-500/30">
          4
        </span>
        <h2
          id="storyboard-heading"
          className="text-lg font-medium text-neutral-100"
        >
          {t.storyboard.heading}
        </h2>
      </div>

      <p className="mb-4 text-xs text-neutral-500">
        {t.storyboard.description}
      </p>

      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="block text-xs font-medium uppercase tracking-widest text-neutral-500">
              {t.storyboard.recommendedPrompts}
            </span>
            <span className="text-[10px] uppercase tracking-widest text-neutral-600">
              {t.storyboard.clickToApply}
            </span>
          </div>
          <div className="mb-3 flex flex-wrap gap-2">
            {t.storyboard.prompts.map((p) => (
              <button
                key={p.label}
                type="button"
                disabled={busy}
                onClick={() => setPrompt(p.prompt)}
                className="rounded-full border border-fuchsia-500/30 bg-fuchsia-500/10 px-3 py-1 text-xs font-medium text-fuchsia-200 transition hover:border-fuchsia-500/60 hover:bg-fuchsia-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                title={p.prompt}
              >
                {p.label}
              </button>
            ))}
          </div>

          <label
            htmlFor="user_prompt"
            className="mb-1 block text-xs font-medium uppercase tracking-widest text-neutral-500"
          >
            {t.storyboard.topicBrief}
          </label>
          <textarea
            id="user_prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder={t.storyboard.placeholder}
            rows={4}
            disabled={busy}
            className="w-full resize-y rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-600 focus:border-fuchsia-500/50 focus:outline-none focus:ring-1 focus:ring-fuchsia-500/30 disabled:opacity-60"
          />
        </div>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
          <div>
            <label
              htmlFor="target_duration"
              className="mb-1 block text-xs font-medium uppercase tracking-widest text-neutral-500"
            >
              {t.storyboard.targetDuration}
            </label>
            <input
              id="target_duration"
              type="number"
              min={2}
              max={120}
              step={1}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value) || 0)}
              disabled={busy}
              className="w-32 rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm text-neutral-100 focus:border-fuchsia-500/50 focus:outline-none focus:ring-1 focus:ring-fuchsia-500/30 disabled:opacity-60"
            />
          </div>
          <button
            type="submit"
            disabled={busy || !prompt.trim()}
            className="w-fit rounded-md bg-fuchsia-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
          >
            {busy ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> {t.storyboard.generating}
              </span>
            ) : storyboard ? (
              t.storyboard.regenerate
            ) : (
              t.storyboard.generate
            )}
          </button>
        </div>

        <p className="text-xs text-neutral-500">
          {t.storyboard.usesStructureBeforeJob}{" "}
          <span className="font-mono text-neutral-300">{jobId}</span>
          {t.storyboard.usesStructureAfterJob}
        </p>
      </form>

      {!storyboard && !busy && !error && (
        <p className="mt-4 rounded-md border border-dashed border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-500">
          {t.storyboard.emptyBeforeButton}{" "}
          <span className="text-neutral-300">{t.storyboard.emptyButton}</span>.
        </p>
      )}

      {busy && (
        <div className="mt-4 rounded-md border border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-400">
          <span className="inline-flex items-center gap-2">
            <Spinner /> {t.storyboard.busy}
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-5 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      {storyboard && <StoryboardView storyboard={storyboard} />}
    </section>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

function StoryboardView({ storyboard }: { storyboard: Storyboard }) {
  const { t } = useLanguage();
  const total = storyboard.actual_duration_seconds || 1;
  return (
    <div className="mt-6 space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-widest text-neutral-500">
          {t.storyboard.title}
        </p>
        <p className="mt-1 text-xl font-medium text-fuchsia-300">
          {storyboard.title}
        </p>
        <p className="mt-2 text-xs text-neutral-500">
          {t.storyboard.summary(
            storyboard.scenes.length,
            storyboard.target_duration_seconds,
            storyboard.actual_duration_seconds.toFixed(2)
          )}{" "}
          &middot;{" "}
          {storyboard.width}×{storyboard.height} @ {storyboard.fps}fps
        </p>
      </div>

      {/* Timeline bar */}
      <div className="relative h-3 w-full overflow-hidden rounded-full bg-neutral-800">
        {storyboard.scenes.map((s, i) => {
          const left = (s.start_time / total) * 100;
          const width = ((s.end_time - s.start_time) / total) * 100;
          return (
            <div
              key={s.scene_id}
              title={t.storyboard.timelineTitle(
                s.scene_id,
                s.start_time.toFixed(2),
                s.end_time.toFixed(2)
              )}
              className="absolute top-0 h-full"
              style={{
                left: `${left}%`,
                width: `${Math.max(width, 0.5)}%`,
                background:
                  i % 2 === 0
                    ? "rgba(217, 70, 239, 0.85)"
                    : "rgba(217, 70, 239, 0.45)",
              }}
            />
          );
        })}
      </div>

      <ol className="space-y-3">
        {storyboard.scenes.map((s, i) => (
          <SceneCard key={s.scene_id} index={i} scene={s} />
        ))}
      </ol>

      <div className="border-t border-neutral-800 pt-4 text-xs text-neutral-500">
        <span className="text-neutral-400">{t.storyboard.storyboardId}</span>{" "}
        <span className="font-mono text-neutral-300">{storyboard.id}</span>
        {storyboard.source_structure_card_ids.length > 0 && (
          <>
            <span className="mx-3">·</span>
            <span className="text-neutral-400">{t.storyboard.sourceCards}</span>{" "}
            <span className="font-mono text-neutral-300">
              {storyboard.source_structure_card_ids.join(", ")}
            </span>
          </>
        )}
      </div>
    </div>
  );
}

function SceneCard({ index, scene }: { index: number; scene: StoryboardScene }) {
  const { t } = useLanguage();

  return (
    <li className="rounded-lg border border-neutral-800 bg-neutral-950/40 p-4">
      <div className="mb-3 flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="font-mono text-sm text-fuchsia-300">
          {String(index + 1).padStart(2, "0")} · {scene.scene_id}
        </span>
        <span className="font-mono text-xs text-neutral-400">
          {t.storyboard.sceneTime(
            scene.start_time.toFixed(2),
            scene.end_time.toFixed(2),
            scene.duration_seconds.toFixed(2)
          )}
        </span>
        <span className="rounded bg-neutral-800 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-neutral-300">
          {scene.layout}
        </span>
      </div>

      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
        {scene.text && (
          <Row label={t.storyboard.text}>
            <span className="text-neutral-100">
              {t.storyboard.quoteText(scene.text)}
            </span>
          </Row>
        )}
        <Row label={t.storyboard.visual}>{scene.visual_description}</Row>
        {scene.asset_prompt && (
          <Row label={t.storyboard.assetPrompt}>
            <span className="font-mono text-xs text-neutral-400">
              {scene.asset_prompt}
            </span>
          </Row>
        )}
        <Row label={t.storyboard.animation}>
          <span className="font-mono text-xs text-neutral-400">
            {scene.animation || t.common.notAvailable}
          </span>
        </Row>
        <Row label={t.storyboard.transition}>
          <span className="font-mono text-xs text-neutral-400">
            {scene.transition || t.common.notAvailable}
          </span>
        </Row>
        {scene.source_structure_card_id && (
          <Row label={t.storyboard.sourceCard}>
            <span className="font-mono text-xs text-neutral-500">
              {scene.source_structure_card_id}
            </span>
          </Row>
        )}
        {scene.source_editing_atoms.length > 0 && (
          <Row label={t.storyboard.sourceAtoms}>
            <span className="flex flex-wrap gap-1">
              {scene.source_editing_atoms.map((a) => (
                <span
                  key={a}
                  className="rounded bg-fuchsia-500/10 px-2 py-0.5 text-xs text-fuchsia-300 ring-1 ring-fuchsia-500/30"
                >
                  {a}
                </span>
              ))}
            </span>
          </Row>
        )}
      </dl>
    </li>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="contents">
      <dt className="text-neutral-500">{label}</dt>
      <dd className="text-neutral-200">{children}</dd>
    </div>
  );
}
