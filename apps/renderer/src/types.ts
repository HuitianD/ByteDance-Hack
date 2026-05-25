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

/**
 * Sidecar bundle resolved by the API before invoking the renderer.
 *
 * Renderer-facing fields are the `*_relative_path(s)` ones: they're
 * relative to the API's DATA_DIR which is mounted at the renderer's
 * `publicDir`, so they can be turned into URLs with `staticFile()`.
 * Absolute paths + /static/ URLs are kept for diagnostics.
 *
 * Optional: when absent the composition falls back to placeholder visuals.
 */
export interface MediaAssets {
  job_id?: string | null;
  /** Absolute filesystem path -- diagnostic only on the renderer side. */
  source_video_path?: string | null;
  /** Path relative to DATA_DIR, e.g. `uploads/<job_id>/original.mp4`. */
  source_video_relative_path?: string | null;
  /** `/static/...` URL exposed by the API; not used by the renderer itself. */
  source_video_static_url?: string | null;

  representative_frame_paths?: string[];
  /** Paths relative to DATA_DIR, e.g. `frames/<job_id>/frame_000.jpg`. */
  representative_frame_relative_paths?: string[];
  representative_frame_static_urls?: string[];
}
