# Structure Schema

This document is the canonical description of the core ViralCraft schemas. The TypeScript source of truth lives in `packages/schemas`. Pydantic mirrors will live in `apps/api/app/schemas/` (to be added).

> **Schema rules**
> 1. Don't casually change field names or types.
> 2. Update both TypeScript and Python definitions in lockstep.
> 3. Update sample JSON under `data/`.
> 4. Update affected API routes and UI components.

## VideoAnalysis

Result of analyzing one uploaded sample video.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | UUID |
| `sourceVideoPath` | string | Path inside `data/uploads/` |
| `durationSec` | number | Total length |
| `fps` | number | Source FPS |
| `width`, `height` | number | Source resolution |
| `scenes` | `SceneSegment[]` | Detected scene boundaries |
| `createdAt` | ISO 8601 string | |

### SceneSegment

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `startSec`, `endSec` | number | |
| `role` | string? | e.g. `"hook"`, `"reveal"`, `"payoff"` |
| `thumbnailPath` | string? | Path inside `data/frames/` |

## StructureCard

A reusable creative structure distilled from one or more analyses.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | UUID |
| `title` | string | Short label |
| `summary` | string | Plain-language description |
| `atoms` | `EditingAtom[]` | Ordered building blocks |
| `sourceAnalysisIds` | string[] | Backlinks |
| `tags` | string[] | Retrieval tags |
| `createdAt` | ISO 8601 | |

### EditingAtom

| Field | Type | Notes |
|-------|------|-------|
| `kind` | string | `"hook"`, `"reveal"`, ... |
| `durationSec` | number | Approximate |
| `notes` | string? | Pacing / overlay hints |

## Storyboard

Generation output. Consumed by the renderer.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | UUID |
| `title` | string | |
| `prompt` | string | Original user brief |
| `retrievedStructureCardIds` | string[] | Cards used during generation |
| `fps`, `width`, `height` | number | Render config |
| `scenes` | `StoryboardScene[]` | Ordered scenes |
| `createdAt` | ISO 8601 | |

### StoryboardScene

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | |
| `durationSec` | number | |
| `layout` | string | Token recognized by renderer |
| `text` | string? | |
| `asset` | string? | Path / URL |
| `transition` | string? | |
| `animation` | string? | |
| `captionStyle` | string? | |
| `sourceStructureCardId` | string? | Card that inspired this scene |

## RenderJob

Lifecycle of rendering a Storyboard to mp4.

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | UUID |
| `storyboardId` | string | |
| `status` | enum | `queued` / `running` / `succeeded` / `failed` / `cancelled` |
| `progress` | number? | 0–100 |
| `outputPath` | string? | Final mp4 path |
| `error` | string? | Set on failure |
| `createdAt`, `updatedAt` | ISO 8601 | |
