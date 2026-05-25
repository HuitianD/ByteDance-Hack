import { WorkflowSection } from "@/components/WorkflowSection";

const STEPS = [
  {
    n: 1,
    title: "Upload Sample Video",
    description:
      "Drop in a short clip. The renderer will reuse this footage as the visual layer of the final mp4.",
  },
  {
    n: 2,
    title: "Analyze Video",
    description:
      "Deterministic, non-LLM: extracts metadata, samples representative frames, and detects scene boundaries.",
  },
  {
    n: 3,
    title: "Extract Structure Card",
    description:
      "Distill the reusable creative structure (hook, pacing, editing atoms) into a knowledge-base card.",
  },
  {
    n: 4,
    title: "Generate Storyboard",
    description:
      "Apply the saved structure to a new brief. The LLM returns a typed storyboard JSON ready for rendering.",
  },
  {
    n: 5,
    title: "Render Final Video",
    description:
      "Remotion renders the storyboard, reusing your source footage and overlaying generated captions, cards, and motion graphics.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-16">
      <header className="mb-12">
        <p className="mb-3 text-sm font-medium uppercase tracking-widest text-fuchsia-400">
          ViralCraft
        </p>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          Transfer the structure of viral short videos to your own ideas.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-neutral-400">
          ViralCraft learns reusable creative structure from example videos and
          applies it to new topics, products, or briefs. Every output is built
          from a structured storyboard JSON, then rendered with your uploaded
          footage as the visual layer.
        </p>

        <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900/40 p-4 text-sm text-neutral-300">
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-fuchsia-400">
            MVP scope
          </p>
          <p>
            This MVP performs <strong>structure transfer + media remixing</strong>{" "}
            — it reuses your uploaded footage as the visual layer and overlays
            generated structure, captions, and motion graphics. It is{" "}
            <strong>not</strong> a pixel-level VFX editor: no face filters,
            object insertion, inpainting, or makeup transfer.
          </p>
        </div>
      </header>

      <div className="mb-14">
        <WorkflowSection />
      </div>

      <section aria-labelledby="workflow-heading">
        <h2
          id="workflow-heading"
          className="mb-6 text-sm font-medium uppercase tracking-widest text-neutral-500"
        >
          Demo workflow
        </h2>

        <ol className="space-y-4">
          {STEPS.map((step) => (
            <li
              key={step.n}
              className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-5 transition hover:border-neutral-700"
            >
              <div className="flex items-start gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-fuchsia-500/10 text-sm font-semibold text-fuchsia-300 ring-1 ring-fuchsia-500/30">
                  {step.n}
                </span>
                <div>
                  <h3 className="text-lg font-medium text-neutral-100">
                    {step.title}
                  </h3>
                  <p className="mt-1 text-sm text-neutral-400">
                    {step.description}
                  </p>
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <footer className="mt-16 border-t border-neutral-900 pt-6 text-xs text-neutral-500">
        Full pipeline wired: upload → analyze → structure card → storyboard → render.
        Source-aware renderer reuses uploaded footage when available.
      </footer>
    </main>
  );
}
