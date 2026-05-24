# ViralCraft Renderer

Remotion-based renderer. Compositions consume **storyboard JSON** as input. The current scaffold ships only a `Placeholder` composition.

## Run Remotion Studio

```bash
npm run dev --workspace apps/renderer
```

## Render the placeholder to mp4

```bash
npm run render --workspace apps/renderer
# → ../../data/renders/placeholder.mp4
```

Requires FFmpeg on PATH.
