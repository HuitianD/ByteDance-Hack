"use client";

import type {
  RenderJob,
  Storyboard,
  StructureCard,
  VideoAnalysis,
  VideoUploadResponse,
} from "@/lib/types";

export type PipelineStepStatus = "pending" | "active" | "done" | "error";

type Props = {
  upload: VideoUploadResponse | null;
  analysis: VideoAnalysis | null;
  card: StructureCard | null;
  storyboard: Storyboard | null;
  render: RenderJob | null;
  /** True when any step is mid-flight; tightens visual state. */
  busy?: boolean;
};

/**
 * Always-on panel summarizing the full pipeline. Sticky at the top of the
 * workflow so the user can see at any moment:
 *   - current job_id
 *   - per-step status
 *   - whether source media was resolved for rendering
 */
export function PipelineSummary({
  upload,
  analysis,
  card,
  storyboard,
  render,
}: Props) {
  const steps: {
    n: number;
    label: string;
    status: PipelineStepStatus;
    note?: string;
  }[] = [
    {
      n: 1,
      label: "Upload",
      status: upload ? "done" : "pending",
      note: upload?.original_filename
        ? `${upload.original_filename}`
        : undefined,
    },
    {
      n: 2,
      label: "Analyze",
      status: analysis ? "done" : upload ? "active" : "pending",
      note: analysis
        ? `${analysis.scenes.length} scenes · ${analysis.frames.length} frames`
        : undefined,
    },
    {
      n: 3,
      label: "Structure card",
      status: card ? "done" : analysis ? "active" : "pending",
      note: card?.pattern_name,
    },
    {
      n: 4,
      label: "Storyboard",
      status: storyboard ? "done" : card ? "active" : "pending",
      note: storyboard
        ? `${storyboard.scenes.length} scenes · ${storyboard.actual_duration_seconds.toFixed(0)}s`
        : undefined,
    },
    {
      n: 5,
      label: "Render",
      status:
        render?.status === "succeeded"
          ? "done"
          : render?.status === "failed"
            ? "error"
            : storyboard
              ? "active"
              : "pending",
      note:
        render?.status === "succeeded" && render.duration_ms
          ? `${(render.duration_ms / 1000).toFixed(1)}s`
          : undefined,
    },
  ];

  const mediaTag = renderMediaTag(render);

  return (
    <section
      aria-label="Pipeline summary"
      className="sticky top-3 z-10 rounded-2xl border border-neutral-800 bg-neutral-950/80 p-4 shadow-lg shadow-black/40 backdrop-blur"
    >
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <div className="flex items-baseline gap-3">
          <span className="text-xs font-medium uppercase tracking-widest text-neutral-500">
            Pipeline
          </span>
          {upload ? (
            <span className="text-xs text-neutral-400">
              job{" "}
              <span className="font-mono text-neutral-200">
                {upload.job_id.slice(0, 8)}…
              </span>
            </span>
          ) : (
            <span className="text-xs text-neutral-500">
              waiting for upload
            </span>
          )}
        </div>
        {mediaTag}
      </div>

      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {steps.map((step) => (
          <li
            key={step.n}
            className="rounded-md border border-neutral-800 bg-neutral-900/60 px-3 py-2"
          >
            <div className="flex items-center gap-2">
              <StatusDot status={step.status} />
              <span className="text-xs uppercase tracking-wider text-neutral-300">
                {step.n}. {step.label}
              </span>
            </div>
            <p className="mt-1 truncate text-[11px] text-neutral-500">
              {step.note ?? statusLabel(step.status)}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function statusLabel(s: PipelineStepStatus): string {
  switch (s) {
    case "done":
      return "complete";
    case "active":
      return "ready";
    case "error":
      return "failed";
    case "pending":
    default:
      return "—";
  }
}

function StatusDot({ status }: { status: PipelineStepStatus }) {
  const cls = {
    pending: "bg-neutral-700",
    active: "bg-amber-400 animate-pulse",
    done: "bg-emerald-400",
    error: "bg-red-400",
  }[status];
  return (
    <span
      aria-label={statusLabel(status)}
      className={`inline-block h-2 w-2 rounded-full ${cls}`}
    />
  );
}

function renderMediaTag(render: RenderJob | null): React.ReactNode {
  if (!render || render.status !== "succeeded") return null;
  const ms = render.media_summary;
  if (!ms) return null;

  if (ms.placeholder_only) {
    return (
      <span className="inline-block rounded-full bg-amber-500/10 px-3 py-0.5 text-[10px] font-medium uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/30">
        Source media: none · placeholder visuals
      </span>
    );
  }

  const parts: string[] = [];
  if (ms.used_source_video) parts.push("video");
  if (ms.used_frames) parts.push(`${ms.frame_count} frames`);

  return (
    <span className="inline-block rounded-full bg-emerald-500/10 px-3 py-0.5 text-[10px] font-medium uppercase tracking-wider text-emerald-300 ring-1 ring-emerald-500/30">
      Source media: {parts.join(" + ")}
    </span>
  );
}
