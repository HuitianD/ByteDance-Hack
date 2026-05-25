/**
 * Wire-format types matching the API response.
 * Mirrors `packages/schemas/src/storyboard.ts` (camelCase canonical) but
 * uses the snake_case shape sent over HTTP and persisted to disk so we can
 * pass the JSON straight through.
 */

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
  source_editing_atoms?: string[];
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
  created_at: string;
}
