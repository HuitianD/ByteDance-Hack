/**
 * API DTOs returned by the FastAPI backend (snake_case on purpose).
 *
 * Domain-level pipeline schemas (canonical camelCase) live in
 * `packages/schemas` and are consumed when those endpoints exist.
 */

export interface VideoUploadResponse {
  job_id: string;
  original_filename: string;
  /** Path of the stored file, relative to the API's DATA_DIR. */
  saved_path: string;
  content_type: string;
  size_bytes: number;
  /** ISO 8601 UTC timestamp. */
  created_at: string;
}

export interface FrameInfo {
  index: number;
  timestamp_seconds: number;
  /** Path relative to DATA_DIR. Served at `<API>/static/<path>`. */
  path: string;
}

export interface SceneSegment {
  id: string;
  start_seconds: number;
  end_seconds: number;
  role?: string | null;
  thumbnail_path?: string | null;
}

export type SceneDetectionMethod = "pyscenedetect" | "time_based";

export interface VideoAnalysis {
  id: string;
  job_id: string;
  source_video_path: string;
  duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  total_frames: number;
  file_size_bytes: number;
  frames: FrameInfo[];
  scenes: SceneSegment[];
  scene_detection_method: SceneDetectionMethod;
  /** ISO 8601 UTC timestamp. */
  created_at: string;
}

export interface EditingAtom {
  kind: string;
  duration_seconds: number;
  notes?: string | null;
}

export interface StructureCard {
  id: string;
  pattern_name: string;
  summary: string;
  hook_type: string;
  narrative_flow: string;
  visual_style: string;
  editing_atoms: EditingAtom[];
  reusable_rules: string[];
  source_video_job_id: string;
  source_segments: string[];
  /** ISO 8601 UTC timestamp. */
  created_at: string;
}

export interface StoryboardScene {
  scene_id: string;
  start_time: number;
  end_time: number;
  duration_seconds: number;
  layout: string;
  text?: string | null;
  visual_description: string;
  animation?: string | null;
  transition?: string | null;
  asset_prompt?: string | null;
  source_structure_card_id?: string | null;
  source_editing_atoms: string[];
}

export interface Storyboard {
  id: string;
  title: string;
  user_prompt: string;
  target_duration_seconds: number;
  actual_duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  scenes: StoryboardScene[];
  source_structure_card_ids: string[];
  /** ISO 8601 UTC timestamp. */
  created_at: string;
}

export interface StoryboardGenerateRequest {
  user_prompt: string;
  target_duration_seconds: number;
  source_job_ids?: string[];
}

export type RenderJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface RenderJob {
  render_job_id: string;
  storyboard_id: string;
  status: RenderJobStatus;
  /** Path relative to DATA_DIR. */
  output_path?: string | null;
  /** Server-absolute URL path; prepend API base URL to play. */
  output_url?: string | null;
  duration_ms?: number | null;
  error?: string | null;
  created_at: string;
}
