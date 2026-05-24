/**
 * RenderJob: tracks the lifecycle of rendering a Storyboard to mp4.
 *
 * Placeholder definition for the initial scaffold.
 */

import type { StoryboardId } from "./storyboard";

export type RenderJobId = string;

export type RenderJobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export interface RenderJob {
  id: RenderJobId;
  storyboardId: StoryboardId;
  status: RenderJobStatus;
  /** 0-100. Optional while queued. */
  progress?: number;
  /** Output mp4 path (set once status === "succeeded"). */
  outputPath?: string;
  /** Error message if status === "failed". */
  error?: string;
  createdAt: string;
  updatedAt: string;
}
