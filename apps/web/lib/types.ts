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
