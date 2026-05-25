"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { RenderJob } from "@/lib/types";

type Props = {
  storyboardId: string;
  storyboardTitle?: string;
  width?: number;
  height?: number;
};

export function RenderStep({
  storyboardId,
  storyboardTitle,
  width = 1080,
  height = 1920,
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
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Render failed (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(`Render failed: ${err.message}`);
      } else {
        setError("Render failed.");
      }
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
          Render video
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="rounded-md bg-rose-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-rose-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
        >
          {busy
            ? "Rendering... (can take 30-90s)"
            : job?.status === "succeeded"
              ? "Re-render"
              : "Render Video"}
        </button>
        <p className="text-xs text-neutral-500">
          Storyboard{" "}
          <span className="font-mono text-neutral-300">{storyboardId}</span>
          {storyboardTitle ? ` — “${storyboardTitle}”` : ""}. Spawns Remotion
          on the API host.
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
