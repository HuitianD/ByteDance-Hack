/**
 * StructureCard: a reusable creative structure distilled from one or more
 * analyzed videos. Stored in the knowledge base and retrieved during
 * storyboard generation.
 *
 * TS canonical schema. Pydantic mirror lives in
 * `apps/api/app/schemas/structure_card.py` (snake_case API surface).
 */

export type StructureCardId = string;

export interface EditingAtom {
  /** Short label, e.g. "hook", "reveal", "callout", "transition", "payoff". */
  kind: string;
  /** Approximate duration in seconds. */
  durationSeconds: number;
  /** Optional notes about pacing, transitions, or text overlays. */
  notes?: string;
}

export interface StructureCard {
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
}
