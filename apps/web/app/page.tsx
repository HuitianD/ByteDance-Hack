import { WorkflowSection } from "@/components/WorkflowSection";

const STEPS = [
  {
    n: 1,
    title: "Upload sample video",
    description:
      "Drop in a short video. We extract frames, detect scenes, and prepare it for analysis.",
  },
  {
    n: 2,
    title: "View analysis timeline",
    description:
      "Inspect detected scenes, pacing, hooks, and editing atoms on a timeline.",
  },
  {
    n: 3,
    title: "Save structure card",
    description:
      "Distill the reusable creative structure into a card stored in the knowledge base.",
  },
  {
    n: 4,
    title: "Generate new storyboard",
    description:
      "Provide a topic or brief. Retrieval picks relevant structure cards and produces a storyboard JSON.",
  },
  {
    n: 5,
    title: "Preview and render final video",
    description:
      "Render the storyboard with Remotion + FFmpeg into a final mp4.",
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
          from a structured storyboard JSON before it&rsquo;s rendered.
        </p>
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
      </footer>
    </main>
  );
}
