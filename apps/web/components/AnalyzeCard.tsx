"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import { localeToDateLocale, useLanguage, type Locale } from "@/lib/i18n";
import type { VideoAnalysis } from "@/lib/types";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatSeconds(s: number, locale: Locale): string {
  if (!isFinite(s)) return "—";
  const m = Math.floor(s / 60);
  const r = s - m * 60;
  if (locale === "zh") {
    if (m > 0) return `${m}分 ${r.toFixed(1)}秒`;
    return `${r.toFixed(2)}秒`;
  }
  if (m > 0) return `${m}m ${r.toFixed(1)}s`;
  return `${r.toFixed(2)}s`;
}

type Props = {
  jobId: string;
  onAnalyzed?: (analysis: VideoAnalysis) => void;
};

export function AnalyzeCard({ jobId, onAnalyzed }: Props) {
  const { t } = useLanguage();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VideoAnalysis | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await api.analyzeVideoBasic(jobId);
      setResult(r);
      onAnalyzed?.(r);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(t.analyze.failedStatus(err.status, err.message));
      } else if (err instanceof Error) {
        setError(t.analyze.failedMessage(err.message));
      } else {
        setError(t.analyze.failedGeneric);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="analyze-heading"
      className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
    >
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 ring-1 ring-fuchsia-500/30">
            2
          </span>
          <h2 id="analyze-heading" className="text-lg font-medium text-neutral-100">
            {t.analyze.heading}
          </h2>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="w-fit rounded-md bg-fuchsia-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
        >
          {busy ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> {t.analyze.analyzing}
            </span>
          ) : result ? (
            t.analyze.rerun
          ) : (
            t.analyze.run
          )}
        </button>
      </div>

      <p className="text-xs text-neutral-500">
        {t.analyze.descriptionBeforeJob}{" "}
        <span className="font-mono text-neutral-300">{jobId}</span>
        {t.analyze.descriptionAfterJob}
      </p>

      {!result && !busy && !error && (
        <p className="mt-4 rounded-md border border-dashed border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-500">
          {t.analyze.emptyBeforeButton}{" "}
          <span className="text-neutral-300">{t.analyze.emptyButton}</span>{" "}
          {t.analyze.emptyAfterButton}
        </p>
      )}

      {busy && !result && (
        <div className="mt-4 rounded-md border border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-400">
          <span className="inline-flex items-center gap-2">
            <Spinner /> {t.analyze.busy}
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

      {result && (
        <div className="mt-6 space-y-6">
          <Metadata result={result} />
          <Frames result={result} />
          <Scenes result={result} />
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

function Metadata({ result }: { result: VideoAnalysis }) {
  const { locale, t } = useLanguage();
  const items: Array<[string, string]> = [
    [t.analyze.duration, formatSeconds(result.duration_seconds, locale)],
    [t.analyze.fps, result.fps.toFixed(2)],
    [t.analyze.resolution, `${result.width} × ${result.height}`],
    [
      t.analyze.totalFrames,
      result.total_frames.toLocaleString(localeToDateLocale(locale)),
    ],
    [t.analyze.fileSize, formatBytes(result.file_size_bytes)],
    [t.analyze.source, result.source_video_path],
  ];
  return (
    <div>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-neutral-500">
        {t.analyze.metadata}
      </h3>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
        {items.map(([k, v]) => (
          <div key={k} className="contents">
            <dt className="text-neutral-500">{k}</dt>
            <dd className="break-all text-neutral-200 font-mono">{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function Frames({ result }: { result: VideoAnalysis }) {
  const { t } = useLanguage();

  if (result.frames.length === 0) {
    return (
      <div>
        <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-neutral-500">
          {t.analyze.frames}
        </h3>
        <p className="text-sm text-neutral-500">{t.analyze.noFrames}</p>
      </div>
    );
  }
  return (
    <div>
      <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-neutral-500">
        {t.analyze.frames} ({result.frames.length})
      </h3>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
        {result.frames.map((f) => (
          <li
            key={f.index}
            className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-950"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={api.staticUrl(f.path)}
              alt={t.analyze.frameAlt(f.timestamp_seconds.toFixed(1))}
              className="aspect-video w-full object-cover"
              loading="lazy"
            />
            <div className="px-2 py-1 text-xs text-neutral-400">
              {t.analyze.frameTimestamp(f.timestamp_seconds.toFixed(1))}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Scenes({ result }: { result: VideoAnalysis }) {
  const { t } = useLanguage();
  const total = result.duration_seconds || 1;
  return (
    <div>
      <h3 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-neutral-500">
        <span>
          {t.analyze.scenes} ({result.scenes.length})
        </span>
        <span className="rounded bg-neutral-800 px-2 py-0.5 text-[10px] font-normal normal-case tracking-normal text-neutral-300">
          {result.scene_detection_method === "pyscenedetect"
            ? "PySceneDetect"
            : t.analyze.timeBasedFallback}
        </span>
      </h3>

      <div
        className="relative h-3 w-full overflow-hidden rounded-full bg-neutral-800"
        aria-hidden
      >
        {result.scenes.map((s, i) => {
          const left = (s.start_seconds / total) * 100;
          const width = ((s.end_seconds - s.start_seconds) / total) * 100;
          return (
            <div
              key={s.id}
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

      <ul className="mt-3 max-h-56 space-y-1 overflow-y-auto pr-1 text-sm">
        {result.scenes.map((s) => (
          <li
            key={s.id}
            className="flex items-baseline gap-3 font-mono text-neutral-300"
          >
            <span className="w-24 text-neutral-500">{s.id}</span>
            <span>
              {t.analyze.sceneRange(
                s.start_seconds.toFixed(2),
                s.end_seconds.toFixed(2)
              )}
            </span>
            <span className="text-neutral-500">
              {t.analyze.sceneDuration(
                (s.end_seconds - s.start_seconds).toFixed(2)
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
