/** HTTP/renderer contract. Snake case deliberately matches persisted Pydantic JSON. */
export interface StoryboardSceneWire {
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
  asset_strategy?: "source_remix" | "generated_video";
  generated_asset_id?: string | null;
}
export interface StoryboardWire {
  id: string;
  title: string;
  user_prompt: string;
  target_duration_seconds: number;
  actual_duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  scenes: StoryboardSceneWire[];
  source_structure_card_ids: string[];
  created_at: string;
  version?: number;
  target_media_job_id?: string | null;
  audio_asset_id?: string | null;
  generation_mode?: "seed" | "mock" | "legacy";
}
export interface WorkspaceJob {
  id: string;
  kind: "analyze" | "learn" | "generate" | "render" | "assets";
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: number;
  updated_at: number;
}
export interface JobSubmission {
  kind: WorkspaceJob["kind"];
  resource_id?: string;
  version?: number;
  storyboard?: {
    user_prompt: string;
    target_duration_seconds: number;
    reference_card_ids: string[];
    target_media_job_id: string;
  };
  scene_ids?: string[];
  reference_frame_id?: string;
  reference_has_no_faces?: boolean;
}
