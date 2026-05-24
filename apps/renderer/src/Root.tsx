import { Composition } from "remotion";
import { Placeholder } from "./Placeholder";

export const RemotionRoot: React.FC = () => {
  return (
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
  );
};
