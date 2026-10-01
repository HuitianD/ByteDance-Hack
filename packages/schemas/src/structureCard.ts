/**
 * StructureCard: a reusable creative structure distilled from one or more
 * analyzed videos. Stored in the knowledge base and retrieved during
 * storyboard generation.
 *
 * TS canonical schema. Pydantic mirror lives in
 * `apps/api/app/schemas/structure_card.py` (snake_case API surface).
 */

export type StructureCardId = string;

export type ReferenceSourceKind =
  | "user_upload"
  | "licensed_reference"
  | "self_authored_demo";
export type StructureAspect =
  | "hook"
  | "pacing"
  | "information_flow"
  | "caption_layout";
export type StructureReviewStatus = "pending" | "approved" | "rejected";
export type StructureReviewMethod = "none" | "human" | "assistant_visual";
export type StructureAnalysisMode = "vision" | "metadata" | "mock";

export interface ReferenceSource {
  kind: ReferenceSourceKind;
  title: string;
  author?: string | null;
  url?: string | null;
  license?: string | null;
  licenseUrl?: string | null;
  mediaUrl?: string | null;
  sha256?: string | null;
  originalDurationSeconds?: number | null;
  excerptStartSeconds: number;
  excerptEndSeconds?: number | null;
  changes: string[];
}

export interface EvidenceFrame {
  index: number;
  timestampSeconds: number;
  url?: string | null;
}

export interface StructureObservation {
  id: string;
  aspect: StructureAspect;
  startSeconds: number;
  endSeconds: number;
  frameIndices: number[];
  sourceSegments: string[];
  observation: string;
}

export interface StructureRule {
  id: string;
  instruction: string;
  evidenceIds: string[];
}

export interface StructureReview {
  status: StructureReviewStatus;
  method: StructureReviewMethod;
  reviewer?: string | null;
  reviewedAt?: string | null;
  notes?: string | null;
}

export interface StructureAnalysis {
  mode: StructureAnalysisMode;
  model?: string | null;
  frameCount: number;
  promptVersion: string;
}

export interface EditingAtom {
  /** Short label, e.g. "hook", "reveal", "callout", "transition", "payoff". */
  kind: string;
  /** Approximate duration in seconds. */
  durationSeconds: number;
  /** Optional notes about pacing, transitions, or text overlays. */
  notes?: string;
}

export interface StructureCard {
  origin?: string;
  schemaVersion?: number;
  version?: number;
  id: StructureCardId;
  /** Short, memorable label for the structure pattern. */
  patternName: string;
  /** 2-3 sentence description. */
  summary: string;
  /** Style of the opening hook. */
  hookType: string;
  /** High-level story arc. */
  narrativeFlow: string;
  /** Aesthetic, pacing, transitions, framing. */
  visualStyle: string;
  /** Ordered building blocks of the structure. */
  editingAtoms: EditingAtom[];
  /** Transferable rules for new topics. */
  reusableRules: string[];
  /** job_id of the source upload this card was distilled from. */
  sourceVideoJobId: string;
  /** Scene IDs from the source VideoAnalysis that informed this card. */
  sourceSegments: string[];
  /** ISO 8601 UTC timestamp. */
  createdAt: string;
  /** Evidence fields are optional so historical cards remain readable. */
  source?: ReferenceSource | null;
  evidenceFrames?: EvidenceFrame[];
  observations?: StructureObservation[];
  rules?: StructureRule[];
  applicability?: string[];
  materialRequirements?: string[];
  limitations?: string[];
  review?: StructureReview | null;
  analysis?: StructureAnalysis | null;
}

/** Snake-case API contracts, shared directly with the web client. */
export interface EditingAtomWire {
  kind: string;
  duration_seconds: number;
  notes?: string | null;
}

export interface ReferenceSourceWire {
  kind: ReferenceSourceKind;
  title: string;
  author?: string | null;
  url?: string | null;
  license?: string | null;
  license_url?: string | null;
  media_url?: string | null;
  sha256?: string | null;
  original_duration_seconds?: number | null;
  excerpt_start_seconds: number;
  excerpt_end_seconds?: number | null;
  changes: string[];
}

export interface EvidenceFrameWire {
  index: number;
  timestamp_seconds: number;
  url?: string | null;
}

export interface StructureObservationWire {
  id: string;
  aspect: StructureAspect;
  start_seconds: number;
  end_seconds: number;
  frame_indices: number[];
  source_segments: string[];
  observation: string;
}

export interface StructureRuleWire {
  id: string;
  instruction: string;
  evidence_ids: string[];
}

export interface StructureReviewWire {
  status: StructureReviewStatus;
  method: StructureReviewMethod;
  reviewer?: string | null;
  reviewed_at?: string | null;
  notes?: string | null;
}

export interface StructureAnalysisWire {
  mode: StructureAnalysisMode;
  model?: string | null;
  frame_count: number;
  prompt_version: string;
}

export interface StructureCardWire {
  origin?: string;
  schema_version?: number;
  version?: number;
  id: StructureCardId;
  pattern_name: string;
  summary: string;
  hook_type: string;
  narrative_flow: string;
  visual_style: string;
  editing_atoms: EditingAtomWire[];
  reusable_rules: string[];
  source_video_job_id: string;
  source_segments: string[];
  created_at: string;
  source?: ReferenceSourceWire | null;
  evidence_frames?: EvidenceFrameWire[];
  observations?: StructureObservationWire[];
  rules?: StructureRuleWire[];
  applicability?: string[];
  material_requirements?: string[];
  limitations?: string[];
  review?: StructureReviewWire | null;
  analysis?: StructureAnalysisWire | null;
}
