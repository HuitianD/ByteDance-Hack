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
  const args = { storyboard: null, output: null, compositionId: "Storyboard" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === "--storyboard") args.storyboard = next();
    else if (a === "--output") args.output = next();
    else if (a === "--composition") args.compositionId = next();
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

Options:
  --composition <id>    Composition id to render (default: Storyboard)
  -h, --help            Show this help

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

  const entryPoint = path.join(__dirname, "src", "index.ts");

  const t0 = Date.now();
  console.log(`[viralcraft-renderer] storyboard=${storyboard.id} scenes=${storyboard.scenes.length}`);
  console.log(`[viralcraft-renderer] entry=${entryPoint}`);
  console.log(`[viralcraft-renderer] output=${outputPath}`);

  const bundleLocation = await bundle({
    entryPoint,
    // Cache outside the project so npm install / git clean don't nuke it.
    outDir: path.join(os.tmpdir(), "viralcraft-remotion-bundle"),
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

  const inputProps = { storyboard };

  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: args.compositionId,
    inputProps,
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
