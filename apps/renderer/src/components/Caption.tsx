import { useCurrentFrame, useVideoConfig } from "remotion";

import { applyAnimation, typeOnText } from "../util/animation";

type Props = {
  text: string;
  animation?: string | null;
  size?: "xl" | "lg" | "md" | "sm";
  align?: "left" | "center" | "right";
  color?: string;
  weight?: number;
  letterSpacing?: number;
  maxWidth?: number;
  /** When true, animate as a progressive character reveal regardless of token. */
  typeOn?: boolean;
};

const SIZE_MAP: Record<NonNullable<Props["size"]>, number> = {
  xl: 130,
  lg: 92,
  md: 64,
  sm: 38,
};

export const Caption: React.FC<Props> = ({
  text,
  animation,
  size = "lg",
  align = "center",
  color = "white",
  weight = 700,
  letterSpacing = -2,
  maxWidth,
  typeOn,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const isTypeOn = typeOn || (animation || "").toLowerCase() === "type-on";

  const { opacity, transform } = applyAnimation(
    isTypeOn ? "fade-in" : animation,
    frame,
    fps,
    durationInFrames
  );

  const visibleText = isTypeOn ? typeOnText(text, frame, fps, 0.1, 28) : text;

  return (
    <div
      style={{
        opacity,
        transform,
        color,
        fontSize: SIZE_MAP[size],
        fontWeight: weight,
        letterSpacing,
        textAlign: align,
        lineHeight: 1.05,
        maxWidth,
        margin: align === "center" ? "0 auto" : undefined,
        fontFamily:
          'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        textShadow: "0 6px 24px rgba(0,0,0,0.45)",
        wordBreak: "break-word",
      }}
    >
      {visibleText}
    </div>
  );
};
