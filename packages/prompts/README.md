# @viralcraft/prompts

Prompt templates used by ViralCraft's LLM adapters.

Each prompt is a Markdown file with documented input variables. Templates
should never embed API keys or runtime secrets.

| File | Purpose |
|------|---------|
| `analyze_video.md` | Turn a per-scene transcript + frame summary into a `VideoAnalysis`. |
| `extract_structure_card.md` | Distill a `VideoAnalysis` into a reusable `StructureCard`. |
| `generate_storyboard.md` | Combine a user brief with retrieved `StructureCard`s into a `Storyboard` JSON. |
