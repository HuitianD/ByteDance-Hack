/**
 * Centralized typed API client.
 *
 * Every component that talks to the backend should go through this module.
 * Do not call `fetch` directly from components.
 */

import type { VideoUploadResponse } from "./types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseOrThrow<T>(res: Response): Promise<T> {
  if (res.ok) {
    return (await res.json()) as T;
  }
  let detail = res.statusText;
  try {
    const body = (await res.json()) as { detail?: unknown };
    if (body && typeof body.detail === "string") {
      detail = body.detail;
    }
  } catch {
    // Non-JSON error body; fall back to statusText.
  }
  throw new ApiError(res.status, detail);
}

export const api = {
  baseUrl: API_BASE_URL,

  async uploadVideo(file: File): Promise<VideoUploadResponse> {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE_URL}/videos/upload`, {
      method: "POST",
      body: form,
    });
    return parseOrThrow<VideoUploadResponse>(res);
  },
};
