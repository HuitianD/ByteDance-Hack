/**
 * Centralized typed API client.
 *
 * Every component that talks to the backend should go through this module.
 * Do not call `fetch` directly from components.
 */

import type {
  RenderJob,
  Storyboard,
  StoryboardGenerateRequest,
  StructureCard,
  VideoAnalysis,
  VideoUploadResponse,
} from "./types";

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

  async analyzeVideoBasic(jobId: string): Promise<VideoAnalysis> {
    const res = await fetch(
      `${API_BASE_URL}/videos/${encodeURIComponent(jobId)}/analyze-basic`,
      { method: "POST" }
    );
    return parseOrThrow<VideoAnalysis>(res);
  },

  async extractStructureCard(jobId: string): Promise<StructureCard> {
    const res = await fetch(
      `${API_BASE_URL}/videos/${encodeURIComponent(jobId)}/extract-structure-card`,
      { method: "POST" }
    );
    return parseOrThrow<StructureCard>(res);
  },

  async generateStoryboard(
    body: StoryboardGenerateRequest
  ): Promise<Storyboard> {
    const res = await fetch(`${API_BASE_URL}/storyboards/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return parseOrThrow<Storyboard>(res);
  },

  async renderStoryboard(storyboardId: string): Promise<RenderJob> {
    const res = await fetch(
      `${API_BASE_URL}/storyboards/${encodeURIComponent(storyboardId)}/render`,
      { method: "POST" }
    );
    return parseOrThrow<RenderJob>(res);
  },

  /** Build a URL for a file under DATA_DIR served by the API. */
  staticUrl(relativePath: string): string {
    const cleaned = relativePath.replace(/^\/+/, "");
    return `${API_BASE_URL}/static/${cleaned}`;
  },

  /**
   * Convert a server-absolute URL path (e.g. "/static/renders/x/final.mp4")
   * into a fully-qualified URL the browser can fetch.
   */
  absoluteUrl(serverPath: string): string {
    if (/^https?:\/\//i.test(serverPath)) return serverPath;
    return `${API_BASE_URL}${serverPath.startsWith("/") ? "" : "/"}${serverPath}`;
  },
};
