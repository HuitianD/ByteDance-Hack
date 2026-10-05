import { ApiError } from "./api";
import type {
  Storyboard,
  StructureCard,
  VideoAnalysis,
  RenderJob,
} from "./types";
import type { JobSubmission, WorkspaceJob } from "@viralcraft/schemas";
export type { WorkspaceJob, JobSubmission };
const host = (
  process.env.NODE_ENV === "production"
    ? ""
    : (process.env.NEXT_PUBLIC_API_BASE_URL ?? "")
)
  .replace(/\/+$/, "")
  .replace(/\/api$/, "");
export const mediaUrl = (path: string) => `${host}${path}`;
export interface Upload {
  id: string;
  job_id: string;
  original_filename: string;
  url: string;
  duration_seconds: number;
  analysis?: VideoAnalysis;
  frames?: { id: string; url: string; timestamp_seconds: number }[];
}
export interface Render extends RenderJob {
  id: string;
  version: number;
}
export interface Workspace {
  uploads: Upload[];
  storyboards: Storyboard[];
  renders: Render[];
  jobs: WorkspaceJob[];
  audio: { id: string; name: string }[];
}
export interface Session {
  authenticated: boolean;
  quota: number;
  used: Record<string, number>;
}
export interface Capabilities {
  planner: { provider: string; configured: boolean };
  retrieval: { configured: boolean };
  video: { enabled: boolean; configured: boolean };
}
export async function request<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const multipart = body instanceof FormData;
  const res = await fetch(`${host}/api${path}`, {
    method: method ?? (body ? "POST" : "GET"),
    credentials: "include",
    headers:
      body && !multipart ? { "Content-Type": "application/json" } : undefined,
    body: body ? (multipart ? body : JSON.stringify(body)) : undefined,
  });
  if (!res.ok) {
    let message = res.statusText;
    try {
      const { detail } = await res.json();
      message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((v: { msg: string }) => v.msg).join("; ")
            : detail?.message || message;
    } catch {
      /* Keep the HTTP status if the proxy returned HTML. */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}
export const trial = {
  session: () => request<Session>("/session"),
  login: (code: string) => request<Session>("/session", { code }),
  workspace: () => request<Workspace>("/workspace"),
  library: () => request<{ cards: StructureCard[]; mode: string }>("/library"),
  status: () => request<Capabilities>("/status"),
  search: (query: string) =>
    request<{ cards: StructureCard[]; mode: string; message?: string }>(
      "/library/search",
      { query },
    ),
  upload: (file: File, audio = false) => {
    const form = new FormData();
    form.append("file", file);
    return request<Upload>(audio ? "/audio/upload" : "/videos/upload", form);
  },
  demo: () => request<Upload>("/demo", {}),
  submit: (body: JobSubmission) => request<WorkspaceJob>("/jobs", body),
  retry: (id: string) => request<WorkspaceJob>(`/jobs/${id}/retry`, {}),
  edit: (board: Storyboard) =>
    request<Storyboard>(
      `/storyboards/${board.id}`,
      {
        version: board.version,
        title: board.title,
        scenes: board.scenes,
        audio_asset_id: board.audio_asset_id ?? null,
      },
      "PATCH",
    ),
  feedback: (storyboard_id: string, rating: string, comment: string) =>
    request<{ saved: boolean }>("/feedback", {
      storyboard_id,
      rating,
      comment,
    }),
};
