# generate_storyboard

Placeholder prompt template.

## Inputs

- `{{user_brief}}` — the user's topic / product / creative request.
- `{{retrieved_cards}}` — array of relevant `StructureCard` JSON objects.

## Output

A JSON object matching the `Storyboard` schema in `@viralcraft/schemas`.

## Template

```
You are a short-video storyboard generator. Apply the structure from the
provided cards to the user's brief and produce a `Storyboard` JSON object
with concrete scenes (duration, layout, text, asset, transition,
animation, captionStyle, sourceStructureCardId).

Brief:
{{user_brief}}

Structure cards:
{{retrieved_cards}}

Return only valid JSON.
```
