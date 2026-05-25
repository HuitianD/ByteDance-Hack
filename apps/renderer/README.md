# ViralCraft Renderer

Remotion-based renderer. The `Storyboard` composition consumes a Storyboard
JSON (matching `apps/api/app/schemas/storyboard.py`) and produces an mp4.

## Compositions

- `Storyboard` — the real one. Driven entirely by `inputProps.storyboard`.
  Resolution / fps / duration are all derived from the storyboard via
  `calculateMetadata`.
- `Placeholder` — original demo composition, kept for backward compat.

Layouts implemented in `src/layouts/`:

- `hook_title`
- `text_over_media`
- `split_compare`
- `feature_card`
- `cta_card`
- `default_scene` (fallback)

The layout normalizer (`src/util/layout.ts`) maps any unknown token (incl.
older mock outputs like `title-card`, `callout`, …) to one of the six.

## Install

```bash
npm install --workspace apps/renderer
```

The first render auto-downloads a Chromium build (~120 MB) into Remotion's
cache. FFmpeg is bundled with `@remotion/renderer`.

## Run Remotion Studio (live preview)

```bash
npm run dev --workspace apps/renderer
```

Opens Studio with the default storyboard preview. Edit any layout in
`src/layouts/` and Studio hot-reloads.

## Render a saved storyboard from the CLI

```bash
node apps/renderer/render.mjs \
  --storyboard data/knowledge_base/storyboards/<storyboard_id>.json \
  --output    data/renders/<storyboard_id>/final.mp4
```

This is the same command the FastAPI render route runs in a subprocess.

## Render the placeholder (legacy)

```bash
npm run render:placeholder --workspace apps/renderer
```

## Troubleshooting

- **`Cannot find module '@remotion/bundler'`** → run `npm install --workspace apps/renderer`.
- **First render hangs at "downloading"** → Remotion is fetching Chromium.
  Subsequent renders use the cached copy.
- **Bundle cache** lives at `$TMPDIR/viralcraft-remotion-bundle`. Delete it
  to force a fresh bundle.
