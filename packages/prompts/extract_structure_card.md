# extract_structure_card

Placeholder prompt template.

## Inputs

- `{{video_analysis}}` — a `VideoAnalysis` JSON object.

## Output

A JSON object matching the `StructureCard` schema in `@viralcraft/schemas`.

## Template

```
You are a creative director. Given the analyzed video below, extract the
reusable creative structure as a `StructureCard`. Focus on transferable
patterns (hook, pacing, payoff) -- not topic-specific details.

Analysis:
{{video_analysis}}

Return only valid JSON.
```
