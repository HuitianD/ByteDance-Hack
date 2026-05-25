/**
 * Layout normalization.
 *
 * The storyboard generator can emit any layout token (canonical from
 * the prompt or legacy from the early mock). The renderer maps everything
 * to one of six canonical layouts; unknowns fall back to `default_scene`.
 */

export type CanonicalLayout =
  | "hook_title"
  | "text_over_media"
  | "split_compare"
  | "feature_card"
  | "cta_card"
  | "default_scene";

const LAYOUT_ALIASES: Record<string, CanonicalLayout> = {
  // canonical pass-through
  hook_title: "hook_title",
  text_over_media: "text_over_media",
  split_compare: "split_compare",
  feature_card: "feature_card",
  cta_card: "cta_card",
  default_scene: "default_scene",

  // common LLM/mock variants we want to render gracefully
  "title-card": "hook_title",
  title_card: "hook_title",
  hook: "hook_title",
  intro: "hook_title",

  "centered-text": "default_scene",
  centered_text: "default_scene",

  "fullscreen-asset": "text_over_media",
  fullscreen_asset: "text_over_media",
  "full-screen": "text_over_media",
  "lower-third-caption": "text_over_media",
  lower_third_caption: "text_over_media",

  split: "split_compare",
  comparison: "split_compare",

  callout: "cta_card",
  cta: "cta_card",
  outro: "cta_card",
};

export function normalizeLayout(raw: string | null | undefined): CanonicalLayout {
  if (!raw) return "default_scene";
  const key = raw.trim().toLowerCase().replace(/\s+/g, "_");
  return LAYOUT_ALIASES[key] ?? "default_scene";
}

/** Stable color seed from a string (FNV-1a). */
export function hashSeed(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

/** Derive two HSL colors for a gradient placeholder background. */
export function gradientFromSeed(seed: string): {
  from: string;
  to: string;
  accent: string;
} {
  const h = hashSeed(seed);
  const hue1 = h % 360;
  const hue2 = (hue1 + 60 + (h % 80)) % 360;
  const accentHue = (hue1 + 180) % 360;
  return {
    from: `hsl(${hue1}, 65%, 18%)`,
    to: `hsl(${hue2}, 70%, 28%)`,
    accent: `hsl(${accentHue}, 80%, 65%)`,
  };
}
