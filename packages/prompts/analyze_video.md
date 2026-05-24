# analyze_video

Placeholder prompt template.

## Inputs

- `{{transcript}}` — full transcript with timestamps.
- `{{scene_summaries}}` — array of per-scene visual summaries.

## Output

A JSON object matching the `VideoAnalysis` schema in `@viralcraft/schemas`.

## Template

```
You are a video analyst. Given the transcript and scene summaries below,
produce a `VideoAnalysis` JSON object describing scene boundaries, pacing,
and the apparent role of each scene.

Transcript:
{{transcript}}

Scenes:
{{scene_summaries}}

Return only valid JSON.
```
