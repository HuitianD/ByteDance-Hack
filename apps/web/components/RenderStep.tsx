"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { RenderJob, RenderMediaSummary } from "@/lib/types";

type Props = {
  storyboardId: string;
  storyboardTitle?: string;
  width?: number;
  height?: number;
  onRendered?: (job: RenderJob) => void;
};

export function RenderStep({
  storyboardId,
  storyboardTitle,
  width = 1080,
  height = 1920,
  onRendered,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<RenderJob | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const r = await api.renderStoryboard(storyboardId);
      setJob(r);
      onRendered?.(r);
    } catch (err) {
      setError(formatRenderError(err));
    } finally {
      setBusy(false);
    }
  }

  const videoUrl =
    job?.output_url && job.status === "succeeded"
      ? api.absoluteUrl(job.output_url)
      : null;

  return (
    <section
      aria-labelledby="render-heading"
      className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
    >
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-rose-500/10 text-sm font-semibold text-rose-300 ring-1 ring-rose-500/30">
          5
        </span>
        <h2 id="render-heading" className="text-lg font-medium text-neutral-100">
          Render final video
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={run}
          disabled={busy}
          aria-busy={busy}
          className="rounded-md bg-rose-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
        >
          {busy ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Rendering... (do not close this tab)
            </span>
          ) : job?.status === "succeeded" ? (
            "Re-render video"
          ) : (
            "Render final video"
          )}
        </button>
        <p className="text-xs text-neutral-500">
          Storyboard{" "}
          <span className="font-mono text-neutral-300">{storyboardId}</span>
          {storyboardTitle ? ` — \u201C${storyboardTitle}\u201D` : ""}.
        </p>
      </div>

      <div className="mt-3 space-y-2">
        <p className="rounded-md border border-rose-500/20 bg-rose-500/5 px-3 py-2 text-xs text-rose-200">
          First render can take <span className="font-medium">60–90 seconds</span>{" "}
          while Remotion bundles the project and Chromium warms up. Subsequent
          renders are much faster.
        </p>
        <p className="rounded-md border border-neutral-800 bg-neutral-950/50 px-3 py-2 text-xs text-neutral-400">
          The renderer reuses uploaded source footage and extracted frames as
          the visual background, and adds generated captions, structure, and
          motion graphics on top. It does <em>not</em> perform pixel-level VFX
          edits (face filters, object compositing, inpainting) in this MVP.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="mt-5 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      {job && (
        <div className="mt-6 space-y-4">
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
            <Row label="Status">
              <StatusPill status={job.status} />
            </Row>
            <Row label="Render job id">
              <span className="font-mono text-xs text-neutral-300">
                {job.render_job_id}
              </span>
            </Row>
            {typeof job.duration_ms === "number" && (
              <Row label="Render time">
                <span className="text-neutral-200">
                  {(job.duration_ms / 1000).toFixed(1)}s
                </span>
              </Row>
            )}
            {job.output_path && (
              <Row label="Output path">
                <span className="font-mono text-xs text-neutral-400">
                  {job.output_path}
                </span>
              </Row>
            )}
            {job.media_summary && (
              <Row label="Media used">
                <MediaSummaryBadge summary={job.media_summary} />
              </Row>
            )}
          </dl>

          {videoUrl && (
            <div className="space-y-2">
              <div className="overflow-hidden rounded-xl border border-neutral-800 bg-black">
                <video
                  controls
                  src={videoUrl}
                  className="mx-auto block max-h-[60vh] w-auto"
                  style={{ aspectRatio: `${width} / ${height}` }}
                />
              </div>
              <p className="text-xs text-neutral-500">
                Direct link:{" "}
                <a
                  href={videoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-neutral-300 underline decoration-dotted hover:text-rose-300"
                >
                  {videoUrl}
                </a>
              </p>
            </div>
          )}
        </div>
      )}
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

function MediaSummaryBadge({ summary }: { summary: RenderMediaSummary }) {
  if (summary.placeholder_only) {
    return (
      <span className="inline-flex flex-wrap items-center gap-2">
        <span className="inline-block rounded-full bg-amber-500/10 px-3 py-0.5 text-xs font-medium uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/30">
          Placeholder visuals
        </span>
        <span className="text-xs text-neutral-500">
          (no source media linked — gradient backgrounds only)
        </span>
      </span>
    );
  }

  const parts: string[] = [];
  if (summary.used_source_video) parts.push("source video");
  if (summary.used_frames) parts.push(`${summary.frame_count} frames`);
  const label = parts.join(" + ") || "placeholder visuals";

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <span className="inline-block rounded-full bg-emerald-500/10 px-3 py-0.5 text-xs font-medium uppercase tracking-wider text-emerald-300 ring-1 ring-emerald-500/30">
        {label}
      </span>
      {summary.source_job_id && (
        <span className="font-mono text-[10px] text-neutral-500">
          job {summary.source_job_id.slice(0, 8)}…
        </span>
      )}
    </span>
  );
}

function StatusPill({ status }: { status: RenderJob["status"] }) {
  const map: Record<RenderJob["status"], string> = {
    queued: "bg-neutral-700/30 text-neutral-300 ring-neutral-600/40",
    running: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
    succeeded: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
    failed: "bg-red-500/10 text-red-300 ring-red-500/30",
    cancelled: "bg-neutral-500/10 text-neutral-300 ring-neutral-500/30",
  };
  return (
    <span
      className={`inline-block rounded-full px-3 py-0.5 text-xs font-medium uppercase tracking-wider ring-1 ${map[status]}`}
    >
      {status}
    </span>
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

/**
 * Map a thrown error from the render request into a single user-friendly
 * sentence + an optional details line so the UI never shows a raw stack
 * trace or JSON blob.
 */
function formatRenderError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "We couldn't find this storyboard on the server. Try generating it again.";
    }
    if (err.status === 503) {
      return "The Remotion renderer isn't installed. Run `npm install --workspace apps/renderer` and retry.";
    }
    if (err.status === 502) {
      return (
        "Render subprocess failed. Open the API logs for the full traceback; " +
        "common causes: Chromium download interrupted or a layout exception."
      );
    }
    return `Render failed (${err.status}): ${err.message}`;
  }
  if (err instanceof Error) {
    return `Render failed: ${err.message}`;
  }
  return "Render failed for an unknown reason.";
}
