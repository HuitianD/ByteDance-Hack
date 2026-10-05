"use client";

import { LanguageToggle } from "@/components/LanguageToggle";
import { TrialStudio } from "@/components/TrialStudio";
import { useLanguage } from "@/lib/i18n";

export default function HomePage() {
  const { locale } = useLanguage();
  const zh = locale === "zh";

  return (
    <main className="mx-auto max-w-4xl px-6 py-20">
      <LanguageToggle />

      <header className="mb-12">
        <p className="mb-3 text-sm font-medium uppercase tracking-widest text-fuchsia-400">
          ViralCraft · Creative studio
        </p>
        <h1 className="text-4xl font-semibold tracking-tight md:text-5xl">
          {zh
            ? "借用好结构，讲你的故事。"
            : "Borrow a structure. Tell your story."}
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-neutral-400">
          {zh
            ? "选一个参考结构，上传自己的素材，再把可编辑的草稿变成一条短视频。"
            : "Choose a reference pattern, add your footage, and turn an editable draft into a finished short video."}
        </p>
      </header>

      <details className="mb-8 rounded-2xl border border-neutral-800 p-5" open>
        <summary className="cursor-pointer font-medium">
          {zh ? "先看看成片" : "See the finished examples"}
        </summary>
        <p className="mt-3 text-sm text-neutral-400">
          {zh
            ? "无需邀请码即可播放。真实 AI 样片使用人工整理结构、真实向量检索与 Seed 故事板；开场由 Seedance 生成，其余使用自制演示素材，最终由 Remotion 合成。另保留两条 mock 草稿样片。"
            : "Watch without an invitation. The live AI example uses curated patterns, real vector retrieval and a Seed storyboard, with a Seedance opening and self-made footage composed by Remotion. Two mock draft examples are also available."}
        </p>
        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          {[
            ["live.mp4", zh ? "15s · 真实 AI 链路" : "15s · Live AI pipeline"],
            ["english.mp4", "15s · English · Mock"],
            ["chinese.mp4", "20s · 中文 · Mock"],
          ].map(([file, title]) => (
            <figure key={file}>
              <video
                className="max-h-72 w-full rounded-lg bg-black"
                controls
                playsInline
                preload="metadata"
                src={`/examples/${file}`}
              />
              <figcaption className="mt-2 text-center text-xs text-neutral-400">
                {title}
              </figcaption>
            </figure>
          ))}
        </div>
      </details>
      <div className="mb-14">
        <TrialStudio />
      </div>

      <footer className="mt-16 border-t border-neutral-900 pt-6 text-xs text-neutral-500">
        {zh
          ? "ViralCraft 试用版 · 结构可追溯，字幕与时间可修改。"
          : "ViralCraft preview · Traceable patterns, editable copy and timing."}
      </footer>
    </main>
  );
}
