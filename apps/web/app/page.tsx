"use client";

import { LanguageToggle } from "@/components/LanguageToggle";
import { WorkflowSection } from "@/components/WorkflowSection";
import { useLanguage } from "@/lib/i18n";

export default function HomePage() {
  const { t } = useLanguage();

  return (
    <main className="mx-auto max-w-4xl px-6 py-20">
      <LanguageToggle />

      <header className="mb-12">
        <p className="mb-3 text-sm font-medium uppercase tracking-widest text-fuchsia-400">
          {t.page.eyebrow}
        </p>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          {t.page.heroTitle}
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-neutral-400">
          {t.page.heroBody}
        </p>

        <div className="mt-6 rounded-xl border border-neutral-800 bg-neutral-900/40 p-4 text-sm text-neutral-300">
          <p className="mb-1 text-xs font-medium uppercase tracking-widest text-fuchsia-400">
            {t.page.mvpLabel}
          </p>
          <p>
            {t.page.mvpBeforeStrong}
            <strong>{t.page.mvpStrong}</strong>
            {t.page.mvpAfterStrong}
            <strong>{t.page.mvpNot}</strong>
            {t.page.mvpAfterNot}
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
          {t.page.workflowHeading}
        </h2>

        <ol className="space-y-4">
          {t.page.steps.map((step) => (
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
        {t.page.footer}
      </footer>
    </main>
  );
}
