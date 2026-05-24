/**
 * VideoAnalysis: result of analyzing an uploaded sample video.
 *
 * Placeholder definition for the initial scaffold. Fields will be expanded
 * once the analysis pipeline is implemented (scene detection, transcript,
 * editing atoms, etc.).
 */

export type SceneSegmentId = string;

export interface SceneSegment {
  id: SceneSegmentId;
  startSec: number;
  endSec: number;
  /** Optional human-readable label describing the scene's role (hook, payoff, ...). */
  role?: string;
  /** Optional thumbnail path relative to the data dir. */
  thumbnailPath?: string;
}

export interface VideoAnalysis {
  id: string;
  sourceVideoPath: string;
  durationSec: number;
  fps: number;
  width: number;
  height: number;
  scenes: SceneSegment[];
  /** ISO 8601 timestamp. */
  createdAt: string;
}
