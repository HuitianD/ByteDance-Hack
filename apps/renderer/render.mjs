#!/usr/bin/env node
/**
 * Programmatic Remotion render CLI.
 *
 * Usage:
 *   node render.mjs --storyboard <path/to/storyboard.json> --output <path/to/out.mp4>
 *
 * Bundles the Remotion entry, selects the `Storyboard` composition with the
 * provided JSON as inputProps, and writes an mp4. Used by the FastAPI render
 * service; can also be run directly for debugging.
 */

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {
    storyboard: null,
    output: null,
    compositionId: "Storyboard",
    mediaAssets: null,
    publicDir: null,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === "--storyboard") args.storyboard = next();
    else if (a === "--output") args.output = next();
    else if (a === "--composition") args.compositionId = next();
    else if (a === "--media-assets") args.mediaAssets = next();
    else if (a === "--public-dir") args.publicDir = next();
    else if (a === "--help" || a === "-h") {
      printUsage();
      process.exit(0);
    }
  }
  return args;
}

function printUsage() {
  console.log(`Usage:
  node render.mjs --storyboard <path/to/storyboard.json> --output <path/to/out.mp4>
                  [--media-assets <path/to/media_assets.json>]
                  [--public-dir <path/to/data_dir>]

Options:
  --composition <id>     Composition id to render (default: Storyboard)
  --media-assets <path>  Sidecar JSON with source video / extracted frame
                         paths to reuse as visual background. When omitted
                         the renderer falls back to placeholder visuals.
  --public-dir <path>    Directory mounted as Remotion's staticFile() root
                         (typically DATA_DIR). Required when media-assets
                         reference relative paths.
  -h, --help             Show this help

Reads the storyboard JSON file and renders it through the Remotion entry
in src/index.ts. Writes an mp4 (h264) to the requested output path.`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.storyboard || !args.output) {
    printUsage();
    process.exit(64);
  }

  const storyboardPath = path.resolve(args.storyboard);
  const outputPath = path.resolve(args.output);

  if (!fs.existsSync(storyboardPath)) {
    console.error(`storyboard JSON not found: ${storyboardPath}`);
    process.exit(66);
  }

  const storyboard = JSON.parse(fs.readFileSync(storyboardPath, "utf-8"));
  if (!storyboard || typeof storyboard !== "object" || !Array.isArray(storyboard.scenes)) {
    console.error("storyboard JSON is missing required 'scenes' array");
    process.exit(65);
  }

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  let mediaAssets = null;
  if (args.mediaAssets) {
    const mediaAssetsPath = path.resolve(args.mediaAssets);
    if (!fs.existsSync(mediaAssetsPath)) {
      console.error(`media assets JSON not found: ${mediaAssetsPath}`);
      process.exit(66);
    }
    try {
      mediaAssets = JSON.parse(fs.readFileSync(mediaAssetsPath, "utf-8"));
    } catch (err) {
      console.error(
        `media assets JSON could not be parsed: ${err && err.message ? err.message : err}`
      );
      process.exit(65);
    }
  }

  const entryPoint = path.join(__dirname, "src", "index.ts");

  const t0 = Date.now();
  console.log(`[viralcraft-renderer] storyboard=${storyboard.id} scenes=${storyboard.scenes.length}`);
  console.log(`[viralcraft-renderer] entry=${entryPoint}`);
  console.log(`[viralcraft-renderer] output=${outputPath}`);
  if (mediaAssets) {
    console.log(
      `[viralcraft-renderer] media job_id=${mediaAssets.job_id || "?"}` +
        ` video=${!!mediaAssets.source_video_relative_path}` +
        ` frames=${(mediaAssets.representative_frame_relative_paths || []).length}`
    );
  } else {
    console.log(`[viralcraft-renderer] media none (placeholder mode)`);
  }

  const publicDir = args.publicDir ? path.resolve(args.publicDir) : undefined;
  if (publicDir && !fs.existsSync(publicDir)) {
    console.error(`--public-dir does not exist: ${publicDir}`);
    process.exit(66);
  }
  if (publicDir) {
    console.log(`[viralcraft-renderer] publicDir=${publicDir}`);
  }

  const bundleLocation = await bundle({
    entryPoint,
    // Cache outside the project so npm install / git clean don't nuke it.
    outDir: path.join(os.tmpdir(), "viralcraft-remotion-bundle"),
    publicDir,
    onProgress: (p) => {
      // throttle: only log on each 10% step
      if (p % 10 === 0) {
        process.stderr.write(`bundle: ${p}%\n`);
      }
    },
  });
  console.log(
    `[viralcraft-renderer] bundle ready in ${Date.now() - t0}ms at ${bundleLocation}`
  );

  const inputProps = mediaAssets
    ? { storyboard, mediaAssets }
    : { storyboard };

  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: args.compositionId,
    inputProps,
    ...(publicDir ? { publicDir } : {}),
  });
  console.log(
    `[viralcraft-renderer] composition: ${composition.id} ${composition.width}x${composition.height} @ ${composition.fps}fps frames=${composition.durationInFrames}`
  );

  let lastLogged = -1;
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: "h264",
    outputLocation: outputPath,
    inputProps,
    overwrite: true,
    ...(publicDir ? { publicDir } : {}),
    chromiumOptions: {
      disableWebSecurity: true,
    },
    onProgress: ({ progress }) => {
      const pct = Math.floor(progress * 100);
      if (pct !== lastLogged && pct % 5 === 0) {
        lastLogged = pct;
        process.stderr.write(`render: ${pct}%\n`);
      }
    },
  });

  console.log(
    `[viralcraft-renderer] done in ${Date.now() - t0}ms -> ${outputPath}`
  );
}

main().catch((err) => {
  console.error("[viralcraft-renderer] FAILED");
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
