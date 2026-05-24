# Demo Script

Target runtime: ~3 minutes.

## 0. Setup (off camera)

- All three dev servers running:
  - `apps/web` on `:3000`
  - `apps/api` on `:8000`
  - `apps/renderer` Studio open
- One sample short video ready in `data/uploads/`.
- One example brief ready ("60s ad for a reusable water bottle, energetic, hook-first").

## 1. The pitch (~20s)

> "Most AI video tools either summarize a video or generate one from a prompt.
> ViralCraft does something different: it learns the **structure** of viral
> short videos and applies it to your own ideas. Every output goes through a
> structured storyboard — no free-form prompt-to-pixels."

## 2. Upload + analyze (~40s)

- Open the homepage. Walk through the 5-step workflow card by card.
- Upload the sample short.
- Show the analysis timeline: scene boundaries, role tags (hook, payoff), pacing.

## 3. Save a structure card (~30s)

- Click "Save structure card."
- Show the generated `StructureCard` JSON: atoms, tags, summary.
- Highlight: this card is reusable across topics.

## 4. Generate a new storyboard (~50s)

- Enter the brief.
- Show retrieval picking the saved card(s).
- Show the generated `Storyboard` JSON, scene by scene, with each scene's
  `sourceStructureCardId` linking back to the card.

## 5. Render (~30s)

- Click "Render."
- Show progress, then the final mp4 inline.
- Note: Remotion consumes the storyboard JSON directly — same renderer, new content.

## 6. Wrap (~10s)

> "Same structure, new topic. That's the whole product."

## Backup talking points

- Adapter-based LLM: swap providers without touching product logic.
- Everything observable in the UI: scenes, cards, retrieval, storyboard.
- Local-first storage; scales up to Chroma / Postgres later.
