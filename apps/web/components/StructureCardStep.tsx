"use client";

import { useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { StructureCard } from "@/lib/types";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

type Props = {
  jobId: string;
  onExtracted?: (card: StructureCard) => void;
};

export function StructureCardStep({ jobId, onExtracted }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [card, setCard] = useState<StructureCard | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setCard(null);
    try {
      const r = await api.extractStructureCard(jobId);
      setCard(r);
      onExtracted?.(r);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`Extraction failed (${err.status}): ${err.message}`);
      } else if (err instanceof Error) {
        setError(`Extraction failed: ${err.message}`);
      } else {
        setError("Extraction failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="structure-card-heading"
      className="rounded-2xl border border-neutral-800 bg-neutral-900/40 p-6"
    >
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 ring-1 ring-fuchsia-500/30">
            3
          </span>
          <h2
            id="structure-card-heading"
            className="text-lg font-medium text-neutral-100"
          >
            Extract structure card
          </h2>
        </div>
        <button
          type="button"
          onClick={run}
          disabled={busy}
          className="rounded-md bg-fuchsia-500 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-fuchsia-400 disabled:cursor-not-allowed disabled:bg-neutral-700 disabled:text-neutral-400"
        >
          {busy ? (
            <span className="inline-flex items-center gap-2">
              <Spinner /> Extracting...
            </span>
          ) : card ? (
            "Re-extract structure card"
          ) : (
            "Extract structure card"
          )}
        </button>
      </div>

      <p className="text-xs text-neutral-500">
        Distills a reusable creative structure (hook, pacing, atoms) from the
        analyzed video. Uses the active LLM provider — set{" "}
        <code className="text-neutral-300">LLM_PROVIDER=mock</code> in{" "}
        <code className="text-neutral-300">apps/api/.env</code> to test without
        live Seed calls.
      </p>

      {!card && !busy && !error && (
        <p className="mt-4 rounded-md border border-dashed border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-500">
          Click <span className="text-neutral-300">Extract structure card</span>{" "}
          to distill the reusable creative pattern for this upload.
        </p>
      )}

      {busy && (
        <div className="mt-4 rounded-md border border-neutral-800 bg-neutral-950/40 p-3 text-xs text-neutral-400">
          <span className="inline-flex items-center gap-2">
            <Spinner /> Calling the LLM and validating the structure card...
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-5 rounded-md border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
        >
          {error}
        </div>
      )}

      {card && <CardDetails card={card} />}
    </section>
  );
}

function Spinner() {
  return (
    <span
      aria-hidden
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
    />
  );
}

function CardDetails({ card }: { card: StructureCard }) {
  return (
    <div className="mt-6 space-y-6">
      <div>
        <p className="text-xs font-medium uppercase tracking-widest text-neutral-500">
          Pattern
        </p>
        <p className="mt-1 font-mono text-xl text-fuchsia-300">
          {card.pattern_name}
        </p>
        <p className="mt-2 text-sm text-neutral-300">{card.summary}</p>
      </div>

      <Field label="Hook type" value={card.hook_type} />
      <Field label="Narrative flow" value={card.narrative_flow} />
      <Field label="Visual style" value={card.visual_style} />

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-neutral-500">
          Editing atoms ({card.editing_atoms.length})
        </h3>
        <ul className="space-y-1 text-sm">
          {card.editing_atoms.map((atom, i) => (
            <li
              key={i}
              className="flex items-baseline gap-3 font-mono text-neutral-300"
            >
              <span className="w-32 text-fuchsia-300">{atom.kind}</span>
              <span className="w-20 text-neutral-400">
                {atom.duration_seconds.toFixed(2)}s
              </span>
              {atom.notes && (
                <span className="text-neutral-500 font-sans">{atom.notes}</span>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-neutral-500">
          Reusable rules ({card.reusable_rules.length})
        </h3>
        <ul className="list-disc space-y-1 pl-5 text-sm text-neutral-300 marker:text-fuchsia-400">
          {card.reusable_rules.map((rule, i) => (
            <li key={i}>{rule}</li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-neutral-500">
          Source segments ({card.source_segments.length})
        </h3>
        {card.source_segments.length === 0 ? (
          <p className="text-sm text-neutral-500">No segments referenced.</p>
        ) : (
          <ul className="flex flex-wrap gap-2 text-xs font-mono">
            {card.source_segments.map((id) => (
              <li
                key={id}
                className="rounded bg-neutral-800 px-2 py-1 text-neutral-300"
              >
                {id}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-neutral-800 pt-4 text-xs text-neutral-500">
        <span className="text-neutral-400">card id:</span>{" "}
        <span className="font-mono text-neutral-300">{card.id}</span>
        <span className="mx-3">·</span>
        <span className="text-neutral-400">source job:</span>{" "}
        <span className="font-mono text-neutral-300">
          {card.source_video_job_id}
        </span>
        <span className="mx-3">·</span>
        <span className="text-neutral-400">created:</span>{" "}
        <span className="text-neutral-300">{formatTime(card.created_at)}</span>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-widest text-neutral-500">
        {label}
      </p>
      <p className="mt-1 text-sm text-neutral-200">{value}</p>
    </div>
  );
}
