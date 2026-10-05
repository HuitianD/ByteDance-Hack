"use client";

import { useRef, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { localeToDateLocale, useLanguage } from "@/lib/i18n";
import type { VideoUploadResponse } from "@/lib/types";

const MAX_BYTES = 200 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatTime(iso: string, locale: string): string {
  try {
    return new Date(iso).toLocaleString(locale);
  } catch {
    return iso;
  }
}

type Props = {
  onUploaded?: (response: VideoUploadResponse) => void;
  onReset?: () => void;
};

export function UploadCard({ onUploaded, onReset }: Props) {
  const { locale, t } = useLanguage();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VideoUploadResponse | null>(null);

  function reset() {
    setFile(null);
    setError(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = "";
    onReset?.();
  }

  function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.files?.[0] ?? null;
    setFile(next);
    setError(null);
    setResult(null);
    if (next) onReset?.();
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    if (!file.type.startsWith("video/")) {
      setError(t.upload.selectedNotVideo);
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(t.upload.fileTooLarge(formatBytes(file.size)));
      return;
    }

    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.uploadVideo(file);
      setResult(res);
      onUploaded?.(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(t.upload.uploadFailedStatus(err.status, err.message));
      } else if (err instanceof Error) {
        setError(t.upload.uploadFailedMessage(err.message));
      } else {
        setError(t.upload.uploadFailedGeneric);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="upload-heading"
      className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
    >
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 ring-1 ring-fuchsia-500/30">
          1
        </span>
        <h2 id="upload-heading" className="text-lg font-medium text-neutral-100">
          {t.upload.heading}
        </h2>
      </div>

      <p className="mb-4 text-xs text-neutral-500">
        {t.upload.description}
      </p>

      <form onSubmit={onSubmit} className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          aria-label={t.upload.fileInputAria}
          onChange={onPick}
          disabled={busy}
          className="sr-only"
        />

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
            className="w-fit rounded-md border border-fuchsia-500/30 bg-fuchsia-500/10 px-4 py-2 text-sm font-medium text-fuchsia-200 transition hover:bg-fuchsia-500/15 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {t.upload.chooseFile}
          </button>
          <span className="min-w-0 truncate text-sm text-neutral-400">
            {file?.name ?? t.upload.noFileSelected}
          </span>
        </div>

        {file && !busy && !result && (
          <p className="text-xs text-neutral-400">
            {t.upload.readyToUpload}{" "}
            <span className="text-neutral-200">{file.name}</span> &middot;{" "}
            {formatBytes(file.size)} &middot; {file.type || t.upload.unknown}
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!file || busy}
            className="rounded-md bg-fuchsia-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
          >
            {busy ? (
              <span className="inline-flex items-center gap-2">
                <Spinner /> {t.upload.uploading}
              </span>
            ) : (
              t.upload.upload
            )}
          </button>
          {(file || result || error) && !busy && (
            <button
              type="button"
              onClick={reset}
              className="text-sm text-neutral-400 hover:text-neutral-200"
            >
              {t.upload.reset}
            </button>
          )}
        </div>

        <p className="text-xs text-neutral-500">
          {t.upload.limitNote} <code>data/uploads/</code>.
        </p>
      </form>

      {error && (
        <div
          role="alert"
          className="mt-5 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      {!file && !result && !error && !busy && (
        <p className="mt-5 rounded-md border border-dashed border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-500">
          {t.upload.emptyState}
        </p>
      )}

      {result && (
        <div className="mt-5 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-4">
          <p className="mb-3 text-sm font-medium text-emerald-300">
            {t.upload.success}
          </p>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
            <dt className="text-neutral-500">{t.upload.jobId}</dt>
            <dd className="break-all font-mono text-neutral-100">
              {result.job_id}
            </dd>
            <dt className="text-neutral-500">{t.upload.filename}</dt>
            <dd className="break-all text-neutral-200">
              {result.original_filename || t.common.unnamed}
            </dd>
            <dt className="text-neutral-500">{t.upload.savedPath}</dt>
            <dd className="break-all font-mono text-neutral-200">
              {result.saved_path}
            </dd>
            <dt className="text-neutral-500">{t.upload.contentType}</dt>
            <dd className="text-neutral-200">{result.content_type}</dd>
            <dt className="text-neutral-500">{t.upload.size}</dt>
            <dd className="text-neutral-200">
              {formatBytes(result.size_bytes)}
            </dd>
            <dt className="text-neutral-500">{t.upload.created}</dt>
            <dd className="text-neutral-200">
              {formatTime(result.created_at, localeToDateLocale(locale))}
            </dd>
          </dl>
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
