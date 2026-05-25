import { AbsoluteFill } from "remotion";

import { Caption } from "../components/Caption";
import { PlaceholderVisual } from "../components/PlaceholderVisual";
import type { StoryboardScene } from "../types";

export const HookTitle: React.FC<{ scene: StoryboardScene }> = ({ scene }) => {
  const text = scene.text || "Hook";

  return (
    <AbsoluteFill>
      <PlaceholderVisual
        seed={`hook:${scene.scene_id}`}
        visualDescription={scene.visual_description}
        assetPrompt={scene.asset_prompt ?? undefined}
        motion
      />
      <AbsoluteFill
        style={{
          alignItems: "center",
          justifyContent: "center",
          padding: 80,
        }}
      >
        <Caption
          text={text}
          animation={scene.animation || "scale-pulse"}
          size="xl"
          weight={800}
          letterSpacing={-3}
          maxWidth={920}
        />
        {scene.source_editing_atoms && scene.source_editing_atoms.length > 0 && (
          <div
            style={{
              marginTop: 36,
              padding: "10px 18px",
              borderRadius: 999,
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.18)",
              color: "rgba(255,255,255,0.85)",
              fontSize: 26,
              fontFamily: "system-ui, sans-serif",
              letterSpacing: 1.5,
              textTransform: "uppercase",
            }}
          >
            {scene.source_editing_atoms.join(" · ")}
          </div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
