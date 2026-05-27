import { useCurrentFrame, useVideoConfig } from "remotion";

import { applyAnimation, typeOnText, wordStagger } from "../util/animation";

export type CaptionTone = "sans" | "serif";

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
  /** Reveal words one at a time on a brief stagger — used for the hook title. */
  staggerWords?: boolean;
  /** Font register. `serif` is reserved for hero beats (hook + CTA). */
  tone?: CaptionTone;
};

const SIZE_MAP: Record<NonNullable<Props["size"]>, number> = {
  xl: 130,
  lg: 92,
  md: 64,
  sm: 38,
};

const SANS_STACK =
  'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
const SERIF_STACK =
  '"Cormorant Garamond", "Playfair Display", "Times New Roman", Georgia, serif';

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
  staggerWords,
  tone = "sans",
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const isTypeOn = typeOn || (animation || "").toLowerCase() === "type-on";

  const { opacity, transform } = applyAnimation(
    isTypeOn || staggerWords ? "fade-in" : animation,
    frame,
    fps,
    durationInFrames
  );

  const fontFamily = tone === "serif" ? SERIF_STACK : SANS_STACK;
  const baseStyle: React.CSSProperties = {
    color,
    fontSize: SIZE_MAP[size],
    fontWeight: weight,
    letterSpacing,
    textAlign: align,
    lineHeight: 1.05,
    maxWidth,
    margin: align === "center" ? "0 auto" : undefined,
    fontFamily,
    textShadow: "0 6px 24px rgba(0,0,0,0.45)",
    wordBreak: "break-word",
  };

  if (staggerWords) {
    const words = wordStagger(text, frame, fps, 0.16, 14);
    return (
      <div style={{ ...baseStyle, opacity, transform }}>
        {words.map((w, i) => (
          <span
            key={`${w.word}-${i}`}
            style={{
              display: "inline-block",
              opacity: w.opacity,
              transform: `translateY(${w.translateY}px)`,
              marginRight: i === words.length - 1 ? 0 : "0.32em",
              willChange: "opacity, transform",
            }}
          >
            {w.word}
          </span>
        ))}
      </div>
    );
  }

  const visibleText = isTypeOn ? typeOnText(text, frame, fps, 0.1, 28) : text;

  return (
    <div style={{ ...baseStyle, opacity, transform }}>{visibleText}</div>
  );
};
