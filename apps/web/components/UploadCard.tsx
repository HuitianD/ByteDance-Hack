"use client";

import { useRef, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { VideoUploadResponse } from "@/lib/types";

const MAX_BYTES = 200 * 1024 * 1024;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

type Props = {
  onUploaded?: (response: VideoUploadResponse) => void;
  onReset?: () => void;
};

export function UploadCard({ onUploaded, onReset }: Props) {
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
      setError("Selected file is not a video.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(`File exceeds the 200 MB limit (${formatBytes(file.size)}).`);
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
        setError(`Upload failed (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(`Upload failed: ${err.message}`);
      } else {
        setError("Upload failed.");
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
          Upload a sample video
        </h2>
      </div>

      <form onSubmit={onSubmit} className="space-y-4">
        <input
          ref={inputRef}
          type="file"
          accept="video/*"
          onChange={onPick}
          disabled={busy}
          className="block w-full text-sm text-neutral-300 file:mr-4 file:rounded-md file:border-0 file:bg-fuchsia-500/10 file:px-4 file:py-2 file:text-sm file:font-medium file:text-fuchsia-300 file:ring-1 file:ring-fuchsia-500/30 hover:file:bg-fuchsia-500/15 disabled:opacity-60"
        />

        {file && !busy && !result && (
          <p className="text-xs text-neutral-400">
            Ready to upload <span className="text-neutral-200">{file.name}</span>{" "}
            &middot; {formatBytes(file.size)} &middot; {file.type || "unknown"}
          </p>
        )}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={!file || busy}
            className="rounded-md bg-fuchsia-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
          >
            {busy ? "Uploading..." : "Upload"}
          </button>
          {(file || result || error) && !busy && (
            <button
              type="button"
              onClick={reset}
              className="text-sm text-neutral-400 hover:text-neutral-200"
            >
              Reset
            </button>
          )}
        </div>

        <p className="text-xs text-neutral-500">
          Max 200 MB. Files stay on your machine under <code>data/uploads/</code>.
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

      {result && (
        <div className="mt-5 rounded-md border border-emerald-500/30 bg-emerald-500/5 p-4">
          <p className="mb-3 text-sm font-medium text-emerald-300">
            Upload successful
          </p>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
            <dt className="text-neutral-500">Job ID</dt>
            <dd className="break-all font-mono text-neutral-100">
              {result.job_id}
            </dd>
            <dt className="text-neutral-500">Filename</dt>
            <dd className="break-all text-neutral-200">
              {result.original_filename || "(unnamed)"}
            </dd>
            <dt className="text-neutral-500">Saved path</dt>
            <dd className="break-all font-mono text-neutral-200">
              {result.saved_path}
            </dd>
            <dt className="text-neutral-500">Content type</dt>
            <dd className="text-neutral-200">{result.content_type}</dd>
            <dt className="text-neutral-500">Size</dt>
            <dd className="text-neutral-200">
              {formatBytes(result.size_bytes)}
            </dd>
            <dt className="text-neutral-500">Created</dt>
            <dd className="text-neutral-200">{formatTime(result.created_at)}</dd>
          </dl>
        </div>
      )}
    </section>
  );
}
