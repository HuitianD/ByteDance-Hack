# Demo Script

Target runtime: **3 minutes**. Designed for a single screen-recording or live walkthrough.

## What ViralCraft is (and is not)

ViralCraft performs **structure transfer + media remixing**:

- Learns the creative structure of a viral short (pacing, hooks, transitions,
  narrative flow) and saves it as a reusable `StructureCard`.
- Generates a new `Storyboard` JSON for the user's topic by applying that
  structure.
- Renders the storyboard with Remotion, **reusing the uploaded source
  footage and extracted frames as the visual layer** and overlaying
  generated captions, title cards, transitions, and CTAs on top.

It is explicitly **not** a pixel-level video editor (see "Out of scope" below).

---

## Off-camera setup checklist

- [ ] `apps/api` running on `:8000`, `apps/web` running on `:3000`.
- [ ] One sample short ready to upload — vertical, 10–30 s, clear visual hook
      (e.g. a beauty close-up, product close-up, or coffee pour).
- [ ] Browser zoom at ~110 % so the pipeline panel and timeline are readable.
- [ ] `LLM_PROVIDER` set (`seed` for live, `mock` for guaranteed-deterministic).
- [ ] DevTools closed, terminal panes minimized but visible if asked.
- [ ] One recommended demo prompt rehearsed (see end of doc).

---

## 3-minute live demo script

### 0:00 – 0:25 — Pitch (~25 s)

> "Most AI video tools either summarize a video or generate one from a prompt.
> ViralCraft does something different: it learns the **structure** of viral
> short videos and applies it to your own ideas. The final video is a remix
> of your uploaded footage with generated captions and motion graphics —
> driven by a structured storyboard, not free-form prompt-to-pixels."

Point at the MVP-scope card on the homepage as you say it.

### 0:25 – 0:55 — Upload + analyze (~30 s)

1. Click **Upload Sample Video**, pick the sample clip.
2. When the green success state appears, narrate the persistent **Pipeline
   panel** at the top: "From now on this panel tracks every step, including
   whether source media was found."
3. Click **Analyze Video**. Walk through what's displayed:
   - Metadata (duration, fps, resolution).
   - Sampled frames grid.
   - Scene timeline with hook / payoff coloring.

### 0:55 – 1:30 — Structure card (~35 s)

1. Click **Extract Structure Card**. (Mock or real Seed both work.)
2. Read out the **pattern name** and the first 2–3 editing atoms.
3. Punchline: "This card is **reusable** — same structure, any topic."

### 1:30 – 2:15 — Storyboard (~45 s)

1. Click the **"Luxury perfume ad"** recommended prompt chip. The brief drops
   into the textarea.
2. Click **Generate Storyboard**.
3. Walk through the storyboard timeline:
   - Scene count + duration vs target.
   - Each scene's layout + `source_structure_card_id` lineage.
4. Highlight: every scene maps back to atoms from the saved card.

### 2:15 – 2:55 — Render (~40 s)

1. Click **Render Final Video**.
2. Acknowledge the 60–90 s warm-up note; talk briefly about the source-aware
   renderer while it works: "The renderer reuses your uploaded footage as the
   visual layer, then overlays generated captions, cards, and CTAs."
3. When it lands, point at:
   - The inline mp4 (clearly the user's footage with new structure).
   - The **Media used** badge: `source video + 8 frames`.
   - The pipeline panel's source-media tag.

### 2:55 – 3:00 — Wrap (~5 s)

> "Same structure, new topic, on top of your own footage. That's the whole
> product."

---

## Recommended demo prompts (one-click in the UI)

These prompts fit the current MVP — they describe **structure and copy
direction**, not pixel-level edits. The UI presents them as buttons above the
brief textarea.

1. **Luxury perfume ad** — `Create a 20-second luxury perfume ad based on
   this beauty close-up video. Keep the cinematic slow reveal, premium mood,
   emotional close-ups, and strong visual hook. Add elegant captions,
   fragrance benefit beats, and a final brand CTA.`
2. **Skincare product ad** — `Generate a skincare product ad using this
   video's soft lighting, close-up rhythm, and premium visual tone. Focus on
   hydration, glow, and a clean CTA.`
3. **AI coding tool promo** — `Create a short AI coding tool promo using
   this video's visual pacing, but replace the message with productivity,
   automation, and developer focus.`
4. **Coffee brand short** — `15s coffee brand short. Warm tones, sensory
   captions, morning-routine arc, end with a CTA to visit the store.`

### Recommended primary demo prompt

> **Create a 20-second luxury perfume ad based on this beauty close-up video.
> Keep the cinematic slow reveal, premium mood, emotional close-ups, and
> strong visual hook. Add elegant captions, fragrance benefit beats, and a
> final brand CTA.**

Pair it with a 10–30 s beauty / fashion / product close-up upload. The render
will use the uploaded clip as the background of the hook + payoff scenes,
extracted frames as Ken-Burns backgrounds for the middle beats, and labeled
"Original Style / Remixed Direction" stills in the split-compare scene.

---

## What the renderer reuses vs. generates

| Layer | Source |
| --- | --- |
| Hook background | Uploaded source video (full-screen) |
| Other backgrounds | Extracted frames with Ken-Burns motion |
| Split-compare panels | Two distinct extracted frames, labeled `ORIGINAL STYLE` / `REMIXED DIRECTION` |
| Layouts | Six Remotion templates (hook_title, text_over_media, feature_card, cta_card, split_compare, default_scene) |
| Captions, animations, transitions | Storyboard JSON + animation utilities |
| Lower-third metadata strip | Computed from the storyboard |

If no source media is resolvable, the renderer falls back to deterministic
gradient placeholders so the demo keeps working — and the Media-used badge
makes this explicit in the UI.

---

## Out of scope

These behaviors are **explicitly not** part of the MVP. Prompts that imply
them should be reframed into structure-and-copy briefs.

- **Face filters / face tracking** (e.g. "make her smile more")
- **Object insertion** (e.g. "place a product bottle in her hand")
- **Clown mask / makeup transfer / virtual try-on**
- **Inpainting / background replacement** of the source footage
- **Pixel-level video editing** of frames
- **True before/after VFX** — the split-compare layout shows two stills from
  the same upload labeled "Original Style / Remixed Direction", not a real
  VFX transformation

These are all reasonable follow-up tracks but require face tracking,
diffusion-based editing, or third-party generative APIs that are out of
scope for the current build.

---

## Troubleshooting during the demo

| Symptom | Likely cause | Quick fix |
| --- | --- | --- |
| Upload step rejects the file | Wrong MIME type or > 200 MB | Re-encode to mp4 and retry |
| Analysis returns 500 | OpenCV can't decode the source | `ffmpeg -i src -c:v libx264 -crf 22 out.mp4`, re-upload |
| Structure-card extraction 502 with HTTP 401 | Bad / missing Seed API key | Set `LLM_PROVIDER=mock` in `apps/api/.env` and restart |
| Structure-card extraction 422 | Live LLM returned malformed JSON | Re-run; if persistent, fall back to mock |
| Storyboard generation 404 | No saved structure card yet | Re-run step 3 |
| Render 503 "Renderer not ready" | `apps/renderer` deps not installed or Chromium download interrupted | `npm install --workspace apps/renderer` |
| Render succeeds but final mp4 looks all-gradient | Storyboard's source structure cards don't map to an upload on disk | Re-run the full pipeline; the card → upload mapping must exist |
| Render times out | First render is bundling + warming Chromium | Wait 60–90 s; the second render is much faster |

---

## Backup talking points

- Adapter-based LLM: swap providers without touching product logic.
- Everything observable in the UI: scenes, cards, retrieval, storyboard, the
  resolved media bundle, and the rendered mp4.
- Local-first storage; scales up to Chroma / Postgres later.
- The `media_assets.json` sidecar next to every render is the audit trail of
  exactly which footage was reused.
