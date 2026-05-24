/**
 * VideoAnalysis: result of the basic analyzer for an uploaded sample video.
 *
 * TS canonical schema. The Pydantic mirror lives in
 * `apps/api/app/schemas/video.py` (snake_case on the API surface).
 */

export type SceneSegmentId = string;

export interface FrameInfo {
  index: number;
  timestampSeconds: number;
  /** Path relative to DATA_DIR. Served at `<API>/static/<path>`. */
  path: string;
}

export interface SceneSegment {
  id: SceneSegmentId;
  startSeconds: number;
  endSeconds: number;
  /** Optional human-readable label describing the scene's role (hook, payoff, ...). */
  role?: string;
  /** Optional thumbnail path relative to DATA_DIR. */
  thumbnailPath?: string;
}

export type SceneDetectionMethod = "pyscenedetect" | "time_based";

export interface VideoAnalysis {
  id: string;
  jobId: string;
  /** Source video path, relative to DATA_DIR. */
  sourceVideoPath: string;
  durationSeconds: number;
  fps: number;
  width: number;
  height: number;
  totalFrames: number;
  fileSizeBytes: number;
  frames: FrameInfo[];
  scenes: SceneSegment[];
  sceneDetectionMethod: SceneDetectionMethod;
  /** ISO 8601 timestamp. */
  createdAt: string;
}
