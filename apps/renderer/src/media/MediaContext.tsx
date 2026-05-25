/**
 * Shared media-asset context. Layouts call `useMediaAssets()` to decide
 * whether to render real footage or fall back to placeholder visuals.
 */

import { createContext, useContext } from "react";
import { staticFile } from "remotion";

import type { MediaAssets } from "../types";

const MediaAssetsContext = createContext<MediaAssets | null>(null);

export const MediaAssetsProvider = MediaAssetsContext.Provider;

export function useMediaAssets(): MediaAssets | null {
  return useContext(MediaAssetsContext);
}

export function hasFrames(assets: MediaAssets | null | undefined): boolean {
  return Boolean(
    assets &&
      assets.representative_frame_relative_paths &&
      assets.representative_frame_relative_paths.length > 0
  );
}

export function hasVideo(assets: MediaAssets | null | undefined): boolean {
  return Boolean(assets && assets.source_video_relative_path);
}

/**
 * Resolve the source video to a URL Chromium can fetch. Returns null when
 * no video asset is available.
 */
export function videoUrl(
  assets: MediaAssets | null | undefined
): string | null {
  if (!assets?.source_video_relative_path) return null;
  return staticFile(assets.source_video_relative_path);
}

/**
 * Resolve a frame to a URL Chromium can fetch by index (with rotation).
 */
export function frameUrlFor(
  assets: MediaAssets | null | undefined,
  index: number
): string | null {
  const list = assets?.representative_frame_relative_paths;
  if (!list || !list.length) return null;
  const i = ((index % list.length) + list.length) % list.length;
  return staticFile(list[i]);
}
