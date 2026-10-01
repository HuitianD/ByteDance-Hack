# Reference methods with inspectable evidence

This is a small, reviewed reference catalog, not a dataset of proven viral ads.
The initial videos are **self-authored demonstrations**. They share existing
generated cup footage but express three different caption/narrative patterns.
They prove that the analyzer receives images and can produce inspectable
methods; they do not validate generalization to real campaigns or performance.

## What is stored

- `manifest.json`: source and provenance, plus external candidates that could not
  be downloaded. A candidate is not an analyzed reference.
- `authoring/`: reproducible demo instructions. These are **never** included in
  the analysis prompt; uploads use a neutral `reference.mp4` filename.
- `analyses/`: objective metadata, sampled-frame times and detected scene ranges.
- `extractions/`: original model-produced cards, kept with pending review.
- `cards/`: current reviewed revisions; the app loads approved revisions.
- `reviews/<slug>/vN.json`: immutable review history. Git retains source history.
- `/references/` assets in `apps/web/public`: actual reference MP4s and sampled
  JPEGs. No private upload or session token is placed in this catalog.

The model receives a maximum of twelve resized JPEG images, labelled with their
actual timestamps, plus objective scene intervals. It does not receive the
authoring script or audio. Scope is opening, information progression, observed
pacing and caption layout. Sparse stills cannot establish exact subtitle onsets,
every cut, continuous movement, music synchronization or audience response.

An observation describes what can be seen and cites frames/scene intervals.
A rule proposes a reusable action and cites observations. Requirements and
limitations belong with the rule: applicability is a hypothesis, not measured
proof. IDs, source hashes, URLs, model provenance and review status are assigned
by the server, never trusted from model output.

## Reproduce without paying for generation

From the repository root after installing the pinned dependencies:

```sh
apps/api/.venv/bin/python scripts/make_reference_demos.py
```

This reuses the bundled cup clip with Remotion; it does not call Seedance.
Existing videos are preserved. Use the script's `--output-dir` option to render
a separate comparison instead of replacing a reference that has evidence.

## Explicitly opt into visual analysis

Configure a vision-capable `SEED_MODEL` and credentials in `apps/api/.env`.
For a newly prepared reference, run:

```sh
apps/api/.venv/bin/python scripts/build_reference_library.py --allow-paid --slug showcase
```

Repeat for `question` and `list`. The script uses the application's upload and
queued learn APIs in an isolated `data/integration/reference-library` workspace.
It stores the task ID before waiting and resumes that task on a subsequent run.
Failed tasks are not silently retried. A new attempt requires a separate data
directory and deliberate preservation of the previous extraction. No operation
in this script approves a card. The generated usage record stays in the ignored
data directory; sanitized acceptance summaries may be committed separately.

## Review before publication

Watch the source; inspect every cited JPEG and timestamp. Check that each
observation is visible, the rule follows from its evidence, unsupported claims
are removed, and material requirements can be fulfilled. If necessary, edit a
copy of the extraction and supply `--edited-card /path/to/copy.json`.

```sh
apps/api/.venv/bin/python scripts/review_reference.py showcase \
  --approve-current --method human --reviewer 'Your name' --status approved \
  --notes 'Describe what you checked and corrected.'
```

`--method human` must be used only by an actual human who performed that review.
`--approve-current` preserves the currently corrected observations and rules;
omit it only when deliberately reviewing the raw extraction or an edited copy.
Assistant visual inspection uses `--method assistant_visual` and is displayed
as AI review. Initial assistant-reviewed cards are **not human-approved**; the
owner should record a human review before treating them as a public launch
catalog. This distinction is retained even when status is `approved`.

Restart the API to synchronize trusted catalog revisions. Changing a card to
pending/rejected, or removing its catalog file, withdraws that catalog-managed
public card. User uploads/cards remain private and untouched. The search route
filters results through current SQLite permissions even if a vector row is old.

An approved demo does not license source reuse for external candidates. Import
those only after obtaining the actual video, preserving its author/license and
recording excerpts or alterations. No third-party video has been analyzed in
the initial demonstration collection.
