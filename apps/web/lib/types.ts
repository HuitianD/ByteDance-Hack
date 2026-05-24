/**
 * API DTOs returned by the FastAPI backend.
 *
 * These mirror Pydantic models in `apps/api/app/schemas/`. Domain-level
 * pipeline schemas (VideoAnalysis, StructureCard, ...) live in
 * `packages/schemas` and are consumed once those endpoints exist.
 */

export interface VideoUploadResponse {
  job_id: string;
  original_filename: string;
  /** Path of the stored file, relative to the API's DATA_DIR. */
  saved_path: string;
  content_type: string;
  size_bytes: number;
  /** ISO 8601 UTC timestamp. */
  created_at: string;
}
