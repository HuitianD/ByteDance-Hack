import { Composition } from "remotion";

import { Placeholder } from "./Placeholder";
import { StoryboardComposition, type StoryboardProps } from "./Storyboard";
import type { Storyboard } from "./types";

/**
 * Default storyboard used by Remotion Studio when no inputProps are passed.
 * Real renders pass inputProps via `selectComposition` / `renderMedia`.
 */
const DEFAULT_STORYBOARD: Storyboard = {
  id: "studio-preview",
  title: "Studio preview",
  user_prompt: "Open Remotion Studio with `npm run dev` to iterate on layouts.",
  target_duration_seconds: 9,
  actual_duration_seconds: 9,
  fps: 30,
  width: 1080,
  height: 1920,
  source_structure_card_ids: [],
  created_at: new Date().toISOString(),
  scenes: [
    {
      scene_id: "scene_000",
      start_time: 0,
      end_time: 3,
      duration_seconds: 3,
      layout: "hook_title",
      text: "ViralCraft",
      visual_description: "Bold gradient with the project name.",
      animation: "scale-pulse",
      transition: "none",
      asset_prompt: "Vertical short hook, dark gradient, bold mark.",
      source_structure_card_id: null,
      source_editing_atoms: ["hook"],
    },
    {
      scene_id: "scene_001",
      start_time: 3,
      end_time: 6,
      duration_seconds: 3,
      layout: "feature_card",
      text: "Storyboard-driven rendering",
      visual_description: "Clean glass card on a soft gradient.",
      animation: "slide-up",
      transition: "fade",
      asset_prompt: "Frosted glass card on subtle pattern.",
      source_structure_card_id: null,
      source_editing_atoms: ["development"],
    },
    {
      scene_id: "scene_002",
      start_time: 6,
      end_time: 9,
      duration_seconds: 3,
      layout: "cta_card",
      text: "Try a real storyboard",
      visual_description: "CTA with arrow pill.",
      animation: "scale-pulse",
      transition: "fade",
      asset_prompt: "High-contrast CTA.",
      source_structure_card_id: null,
      source_editing_atoms: ["payoff"],
    },
  ],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Storyboard"
        component={StoryboardComposition}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ storyboard: DEFAULT_STORYBOARD } satisfies StoryboardProps}
        calculateMetadata={({ props }) => {
          const sb = props.storyboard;
          const fps = sb.fps || 30;
          const totalSeconds =
            sb.actual_duration_seconds ||
            sb.scenes.reduce((acc, s) => acc + (s.duration_seconds || 0), 0) ||
            sb.target_duration_seconds ||
            1;
          return {
            durationInFrames: Math.max(1, Math.round(totalSeconds * fps)),
            fps,
            width: sb.width || 1080,
            height: sb.height || 1920,
          };
        }}
      />

      {/* Original placeholder kept for backward-compatible renders. */}
      <Composition
        id="Placeholder"
        component={Placeholder}
        durationInFrames={150}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          title: "ViralCraft",
          subtitle: "Storyboard-driven video rendering",
        }}
      />
    </>
  );
};
