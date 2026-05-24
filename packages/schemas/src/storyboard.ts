/**
 * Storyboard: the structured output produced from a user request plus
 * retrieved structure cards. The renderer consumes this directly.
 *
 * Placeholder definition for the initial scaffold.
 */

import type { StructureCardId } from "./structureCard";

export type StoryboardId = string;

export interface StoryboardScene {
  id: string;
  /** Duration of this scene in seconds. */
  durationSec: number;
  /** Layout token, e.g. "centered-text", "split", "fullscreen-asset". */
  layout: string;
  /** Optional on-screen text. */
  text?: string;
  /** Optional asset reference (image/video/audio path or URL). */
  asset?: string;
  /** Optional transition into this scene. */
  transition?: string;
  /** Optional animation token applied to the scene's primary element. */
  animation?: string;
  /** Optional caption style token. */
  captionStyle?: string;
  /** Which structure card inspired this scene. */
  sourceStructureCardId?: StructureCardId;
}

export interface Storyboard {
  id: StoryboardId;
  title: string;
  /** The original user request / brief. */
  prompt: string;
  /** Structure cards retrieved and used during generation. */
  retrievedStructureCardIds: StructureCardId[];
  fps: number;
  width: number;
  height: number;
  scenes: StoryboardScene[];
  createdAt: string;
}
