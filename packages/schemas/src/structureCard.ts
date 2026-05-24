/**
 * StructureCard: a reusable creative structure distilled from one or more
 * analyzed videos. Stored in the knowledge base and retrieved during
 * storyboard generation.
 *
 * Placeholder definition for the initial scaffold.
 */

export type StructureCardId = string;

export interface EditingAtom {
  /** Short label, e.g. "hook", "reveal", "callout". */
  kind: string;
  /** Approximate duration in seconds. */
  durationSec: number;
  /** Optional notes about pacing, transitions, or text overlays. */
  notes?: string;
}

export interface StructureCard {
  id: StructureCardId;
  title: string;
  summary: string;
  /** Ordered editing atoms that describe the reusable structure. */
  atoms: EditingAtom[];
  /** Source analyses this card was distilled from. */
  sourceAnalysisIds: string[];
  /** Free-form tags for retrieval ("ugc", "hook-first", "product-reveal", ...). */
  tags: string[];
  createdAt: string;
}
