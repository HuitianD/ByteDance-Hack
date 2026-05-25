/**
 * RenderJob: tracks the lifecycle of rendering a Storyboard to mp4.
 *
 * Wire format (snake_case) matches the Pydantic schema in
 * `apps/api/app/schemas/render_job.py`.
 */

import type { StoryboardId } from "./storyboard";

export type RenderJobId = string;

export type RenderJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

/**
 * Compact summary of which source media was reused for a render.
 * Mirrors `app.schemas.render_job.RenderMediaSummary` on the API side.
 */
export interface RenderMediaSummary {
  used_source_video: boolean;
  used_frames: boolean;
  frame_count: number;
  source_job_id?: string | null;
  placeholder_only: boolean;
}

export interface RenderJob {
  render_job_id: RenderJobId;
  storyboard_id: StoryboardId;
  status: RenderJobStatus;

  /** Path to the rendered mp4 relative to DATA_DIR. */
  output_path?: string | null;
  /** Server-absolute URL path; frontend prepends API base URL. */
  output_url?: string | null;

  duration_ms?: number | null;
  error?: string | null;

  media_summary?: RenderMediaSummary | null;

  /** ISO 8601 UTC timestamp. */
  created_at: string;
}
