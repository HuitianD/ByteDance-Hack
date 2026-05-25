/**
 * Storyboard: the generation output that drives the Remotion renderer.
 *
 * TS canonical schema. Pydantic mirror lives in
 * `apps/api/app/schemas/storyboard.py` (snake_case API surface).
 */

import type { StructureCardId } from "./structureCard";

export type StoryboardId = string;

export interface StoryboardScene {
  sceneId: string;
  startTime: number;
  endTime: number;
  durationSeconds: number;

  /** Layout token consumed by the renderer. */
  layout: string;
  /** Optional on-screen text. */
  text?: string;
  /** Plain-language description of what should be on screen. */
  visualDescription: string;
  /** Animation token applied to the scene's primary element. */
  animation?: string;
  /** Transition into this scene. */
  transition?: string;
  /** Prompt for generating the scene's visual asset. */
  assetPrompt?: string;

  /** StructureCard id this scene was derived from. */
  sourceStructureCardId?: StructureCardId;
  /** Editing-atom kinds (e.g. "hook", "reveal") referenced by this scene. */
  sourceEditingAtoms: string[];
}

export interface Storyboard {
  id: StoryboardId;
  title: string;
  userPrompt: string;
  targetDurationSeconds: number;
  actualDurationSeconds: number;

  fps: number;
  width: number;
  height: number;

  scenes: StoryboardScene[];
  sourceStructureCardIds: StructureCardId[];

  /** ISO 8601 UTC timestamp. */
  createdAt: string;
}
