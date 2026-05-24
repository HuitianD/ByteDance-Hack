import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type PlaceholderProps = {
  title: string;
  subtitle: string;
};

export const Placeholder: React.FC<PlaceholderProps> = ({
  title,
  subtitle,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const titleScale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6 },
  });

  const subtitleOpacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateRight: "clamp",
  });

  const fadeOut = interpolate(
    frame,
    [durationInFrames - 20, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(160deg, #0b0b14 0%, #1a0f2e 55%, #2a0a3a 100%)",
        opacity: fadeOut,
        fontFamily:
          'system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: "white",
        alignItems: "center",
        justifyContent: "center",
        padding: 80,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: 140,
          fontWeight: 700,
          letterSpacing: -3,
          transform: `scale(${titleScale})`,
        }}
      >
        {title}
      </div>
      <div
        style={{
          marginTop: 24,
          fontSize: 44,
          fontWeight: 400,
          opacity: subtitleOpacity,
          color: "#d6c8ff",
        }}
      >
        {subtitle}
      </div>
      <div
        style={{
          marginTop: 80,
          fontSize: 26,
          opacity: subtitleOpacity * 0.7,
          color: "#9ea3b0",
        }}
      >
        Placeholder composition · replace with storyboard-driven scenes
      </div>
    </AbsoluteFill>
  );
};
