import {
  AbsoluteFill,
  Sequence,
  Series,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

import { CtaCard } from "./layouts/CtaCard";
import { DefaultScene } from "./layouts/DefaultScene";
import { FeatureCard } from "./layouts/FeatureCard";
import { HookTitle } from "./layouts/HookTitle";
import { SplitCompare } from "./layouts/SplitCompare";
import { TextOverMedia } from "./layouts/TextOverMedia";
import { MediaAssetsProvider } from "./media/MediaContext";
import type {
  MediaAssets,
  Storyboard as StoryboardType,
  StoryboardScene,
} from "./types";
import { applyTransitionIn } from "./util/animation";
import { normalizeLayout } from "./util/layout";

export type StoryboardProps = {
  storyboard: StoryboardType;
  mediaAssets?: MediaAssets | null;
};

export const StoryboardComposition: React.FC<StoryboardProps> = ({
  storyboard,
  mediaAssets,
}) => {
  const { fps } = useVideoConfig();

  return (
    <MediaAssetsProvider value={mediaAssets ?? null}>
      <AbsoluteFill style={{ background: "#04050a" }}>
        <Series>
          {storyboard.scenes.map((scene, sceneIndex) => {
            const frames = Math.max(
              1,
              Math.round(scene.duration_seconds * fps)
            );
            return (
              <Series.Sequence
                key={scene.scene_id}
                durationInFrames={frames}
                name={`${scene.scene_id}:${scene.layout}`}
              >
                <SceneContainer scene={scene} sceneIndex={sceneIndex} />
              </Series.Sequence>
            );
          })}
        </Series>

        {/* Lower-third metadata strip; tiny, observable, doesn't fight content. */}
        <MetadataStrip storyboard={storyboard} />
      </AbsoluteFill>
    </MediaAssetsProvider>
  );
};

const SceneContainer: React.FC<{
  scene: StoryboardScene;
  sceneIndex: number;
}> = ({ scene, sceneIndex }) => {
  const frame = useCurrentFrame();
  const layout = normalizeLayout(scene.layout);
  const transitionOpacity = applyTransitionIn(scene.transition, frame);

  let inner: React.ReactNode;
  switch (layout) {
    case "hook_title":
      inner = <HookTitle scene={scene} sceneIndex={sceneIndex} />;
      break;
    case "text_over_media":
      inner = <TextOverMedia scene={scene} sceneIndex={sceneIndex} />;
      break;
    case "split_compare":
      inner = <SplitCompare scene={scene} sceneIndex={sceneIndex} />;
      break;
    case "feature_card":
      inner = <FeatureCard scene={scene} sceneIndex={sceneIndex} />;
      break;
    case "cta_card":
      inner = <CtaCard scene={scene} sceneIndex={sceneIndex} />;
      break;
    case "default_scene":
    default:
      inner = <DefaultScene scene={scene} sceneIndex={sceneIndex} />;
      break;
  }

  return (
    <AbsoluteFill style={{ opacity: transitionOpacity }}>{inner}</AbsoluteFill>
  );
};

/**
 * Always-on lower-third strip that shows the storyboard title +
 * scene index. Helps debugging / makes the demo "observable".
 */
const MetadataStrip: React.FC<{ storyboard: StoryboardType }> = ({
  storyboard,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const seconds = frame / fps;

  let activeIndex = 0;
  for (let i = 0; i < storyboard.scenes.length; i++) {
    if (seconds >= storyboard.scenes[i].start_time) {
      activeIndex = i;
    } else {
      break;
    }
  }
  const total = storyboard.scenes.length;

  return (
    <Sequence from={0}>
      <div
        style={{
          position: "absolute",
          bottom: 28,
          left: 32,
          right: 32,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          color: "rgba(255,255,255,0.65)",
          fontFamily: "system-ui, sans-serif",
          fontSize: 22,
          letterSpacing: 0.5,
          textShadow: "0 2px 8px rgba(0,0,0,0.5)",
        }}
      >
        <span>{truncate(storyboard.title, 60)}</span>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          {String(activeIndex + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </span>
      </div>
    </Sequence>
  );
};

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trimEnd()}…`;
}
