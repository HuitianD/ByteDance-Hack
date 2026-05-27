"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Locale = "en" | "zh";

const en = {
  common: {
    languageToggleAria: "Switch interface language",
    unnamed: "(unnamed)",
    notAvailable: "—",
    seconds: (value: string) => `${value}s`,
  },
  page: {
    eyebrow: "ViralCraft",
    heroTitle:
      "Transfer the structure of viral short videos to your own ideas.",
    heroBody:
      "ViralCraft learns reusable creative structure from example videos and applies it to new topics, products, or briefs. Every output is built from a structured storyboard JSON, then rendered with your uploaded footage as the visual layer.",
    mvpLabel: "MVP scope",
    mvpBeforeStrong: "This MVP performs ",
    mvpStrong: "structure transfer + media remixing",
    mvpAfterStrong:
      " - it reuses your uploaded footage as the visual layer and overlays generated structure, captions, and motion graphics. It is ",
    mvpNot: "not",
    mvpAfterNot:
      " a pixel-level VFX editor: no face filters, object insertion, inpainting, or makeup transfer.",
    workflowHeading: "Demo workflow",
    footer:
      "Full pipeline wired: upload -> analyze -> structure card -> storyboard -> render. Source-aware renderer reuses uploaded footage when available.",
    steps: [
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
    ],
  },
  upload: {
    heading: "Upload sample video",
    description:
      "Pick a short vertical clip (5-60s ideal). The renderer will reuse this footage as the visual background of the final mp4.",
    chooseFile: "Choose video",
    fileInputAria: "Choose a video file",
    noFileSelected: "No file selected",
    selectedNotVideo: "Selected file is not a video.",
    fileTooLarge: (size: string) =>
      `File exceeds the 200 MB limit (${size}).`,
    readyToUpload: "Ready to upload",
    unknown: "unknown",
    upload: "Upload",
    uploading: "Uploading...",
    reset: "Reset",
    limitNote: "Max 200 MB. Files stay on your machine under",
    emptyState: "No file picked yet. Choose a video to start the pipeline.",
    uploadFailedStatus: (status: number, message: string) =>
      `Upload failed (${status}): ${message}`,
    uploadFailedMessage: (message: string) => `Upload failed: ${message}`,
    uploadFailedGeneric: "Upload failed.",
    success: "Upload successful - continue to step 2",
    jobId: "Job ID",
    filename: "Filename",
    savedPath: "Saved path",
    contentType: "Content type",
    size: "Size",
    created: "Created",
  },
  pipeline: {
    ariaLabel: "Pipeline summary",
    title: "Pipeline",
    job: "job",
    waitingForUpload: "waiting for upload",
    steps: {
      upload: "Upload",
      analyze: "Analyze",
      structureCard: "Structure card",
      storyboard: "Storyboard",
      render: "Render",
    },
    analysisNote: (scenes: number, frames: number) =>
      `${scenes} scenes · ${frames} frames`,
    storyboardNote: (scenes: number, seconds: number) =>
      `${scenes} scenes · ${seconds}s`,
    statusLabel: {
      done: "complete",
      active: "ready",
      error: "failed",
      pending: "—",
    },
    sourceMediaNone: "Source media: none · placeholder visuals",
    sourceMedia: (parts: string) => `Source media: ${parts}`,
    video: "video",
    frames: (count: number) => `${count} frames`,
  },
  analyze: {
    heading: "Analyze video",
    analyzing: "Analyzing...",
    rerun: "Re-run analysis",
    run: "Analyze video",
    descriptionBeforeJob:
      "Deterministic, non-LLM: extracts metadata, samples representative frames, and segments scenes. Job",
    descriptionAfterJob: ".",
    emptyBeforeButton: "Click",
    emptyButton: "Analyze video",
    emptyAfterButton: "to extract frames + scenes. This unlocks step 3.",
    busy: "Sampling frames and detecting scene boundaries...",
    failedStatus: (status: number, message: string) =>
      `Analysis failed (${status}): ${message}`,
    failedMessage: (message: string) => `Analysis failed: ${message}`,
    failedGeneric: "Analysis failed.",
    metadata: "Metadata",
    duration: "Duration",
    fps: "FPS",
    resolution: "Resolution",
    totalFrames: "Total frames",
    fileSize: "File size",
    source: "Source",
    frames: "Frames",
    noFrames: "No frames extracted.",
    frameAlt: (seconds: string) => `Frame at ${seconds}s`,
    frameTimestamp: (seconds: string) => `t = ${seconds}s`,
    scenes: "Scenes",
    sceneRange: (start: string, end: string) => `${start}s -> ${end}s`,
    sceneDuration: (seconds: string) => `(${seconds}s)`,
    timeBasedFallback: "Time-based fallback",
  },
  structure: {
    heading: "Extract structure card",
    extracting: "Extracting...",
    reextract: "Re-extract structure card",
    extract: "Extract structure card",
    descriptionBeforeCode:
      "Distills a reusable creative structure (hook, pacing, atoms) from the analyzed video. Uses the active LLM provider. Set",
    descriptionBetweenCode: "in",
    descriptionAfterCode: " to test without live Seed calls.",
    emptyBeforeButton: "Click",
    emptyButton: "Extract structure card",
    emptyAfterButton:
      "to distill the reusable creative pattern for this upload.",
    busy: "Calling the LLM and validating the structure card...",
    failedStatus: (status: number, message: string) =>
      `Extraction failed (${status}): ${message}`,
    failedMessage: (message: string) => `Extraction failed: ${message}`,
    failedGeneric: "Extraction failed.",
    pattern: "Pattern",
    hookType: "Hook type",
    narrativeFlow: "Narrative flow",
    visualStyle: "Visual style",
    editingAtoms: (count: number) => `Editing atoms (${count})`,
    reusableRules: (count: number) => `Reusable rules (${count})`,
    sourceSegments: (count: number) => `Source segments (${count})`,
    noSegments: "No segments referenced.",
    cardId: "card id:",
    sourceJob: "source job:",
    created: "created:",
  },
  storyboard: {
    heading: "Generate storyboard",
    description:
      "Describe what you want the new video to be about. The LLM applies the extracted structure to your topic and outputs a typed storyboard JSON.",
    recommendedPrompts: "Recommended demo prompts",
    clickToApply: "click to apply",
    topicBrief: "Topic / brief",
    placeholder:
      "e.g. 20-second luxury perfume ad - cinematic slow reveals, premium mood, emotional close-ups, strong visual hook.",
    targetDuration: "Target duration (seconds)",
    generating: "Generating...",
    regenerate: "Re-generate storyboard",
    generate: "Generate storyboard",
    usesStructureBeforeJob: "Uses the structure card from job",
    usesStructureAfterJob: ". LLM call goes through the active provider.",
    emptyBeforeButton:
      "Pick a recommended prompt or write your own brief, then click",
    emptyButton: "Generate storyboard",
    busy:
      "Asking the LLM for a structured storyboard and validating each scene...",
    promptRequired: "Please enter a prompt.",
    failedStatus: (status: number, message: string) =>
      `Generation failed (${status}): ${message}`,
    failedMessage: (message: string) => `Generation failed: ${message}`,
    failedGeneric: "Generation failed.",
    title: "Title",
    summary: (scenes: number, target: number, actual: string) =>
      `${scenes} scenes · target ${target}s · actual ${actual}s`,
    timelineTitle: (sceneId: string, start: string, end: string) =>
      `${sceneId}: ${start}s -> ${end}s`,
    sceneTime: (start: string, end: string, duration: string) =>
      `${start}s -> ${end}s (${duration}s)`,
    storyboardId: "storyboard id:",
    sourceCards: "source cards:",
    text: "Text",
    quoteText: (text: string) => `“${text}”`,
    visual: "Visual",
    assetPrompt: "Asset prompt",
    animation: "Animation",
    transition: "Transition",
    sourceCard: "Source card",
    sourceAtoms: "Source atoms",
    prompts: [
      {
        label: "Luxury perfume ad",
        prompt:
          "Create a 20-second luxury perfume ad based on this beauty close-up video. Keep the cinematic slow reveal, premium mood, emotional close-ups, and strong visual hook. Add elegant captions, fragrance benefit beats, and a final brand CTA.",
      },
      {
        label: "Skincare product ad",
        prompt:
          "Generate a skincare product ad using this video's soft lighting, close-up rhythm, and premium visual tone. Focus on hydration, glow, and a clean CTA.",
      },
      {
        label: "AI coding tool promo",
        prompt:
          "Create a short AI coding tool promo using this video's visual pacing, but replace the message with productivity, automation, and developer focus.",
      },
    ],
  },
  render: {
    heading: "Render final video",
    rendering: "Rendering... (do not close this tab)",
    rerender: "Re-render video",
    render: "Render final video",
    storyboard: "Storyboard",
    firstRenderBeforeTime: "First render can take",
    firstRenderTime: "60-90 seconds",
    firstRenderAfterTime:
      "while Remotion bundles the project and Chromium warms up. Subsequent renders are much faster.",
    mvpNoteBeforeEm:
      "The renderer reuses uploaded source footage and extracted frames as the visual background, and adds generated captions, structure, and motion graphics on top. It does",
    mvpNoteEm: "not",
    mvpNoteAfterEm:
      "perform pixel-level VFX edits (face filters, object compositing, inpainting) in this MVP.",
    status: "Status",
    renderJobId: "Render job id",
    renderTime: "Render time",
    outputPath: "Output path",
    mediaUsed: "Media used",
    directLink: "Direct link:",
    placeholderVisuals: "Placeholder visuals",
    noSourceMedia: "(no source media linked - gradient backgrounds only)",
    sourceVideo: "source video",
    frames: (count: number) => `${count} frames`,
    placeholderVisualsLower: "placeholder visuals",
    job: "job",
    statusLabels: {
      queued: "queued",
      running: "running",
      succeeded: "succeeded",
      failed: "failed",
      cancelled: "cancelled",
    },
    error404:
      "We couldn't find this storyboard on the server. Try generating it again.",
    error503:
      "The Remotion renderer isn't installed. Run `npm install --workspace apps/renderer` and retry.",
    error502:
      "Render subprocess failed. Open the API logs for the full traceback; common causes: Chromium download interrupted or a layout exception.",
    failedStatus: (status: number, message: string) =>
      `Render failed (${status}): ${message}`,
    failedMessage: (message: string) => `Render failed: ${message}`,
    failedUnknown: "Render failed for an unknown reason.",
  },
};

export type Copy = typeof en;

const zh: Copy = {
  common: {
    languageToggleAria: "切换界面语言",
    unnamed: "（未命名）",
    notAvailable: "—",
    seconds: (value: string) => `${value} 秒`,
  },
  page: {
    eyebrow: "ViralCraft",
    heroTitle: "把爆款短视频的结构迁移到你的创意上。",
    heroBody:
      "ViralCraft 会从样例视频中学习可复用的创意结构，并应用到新的主题、产品或创作简报。每个输出都会先生成结构化 storyboard JSON，再用你上传的素材作为视觉层进行渲染。",
    mvpLabel: "MVP 范围",
    mvpBeforeStrong: "当前 MVP 支持",
    mvpStrong: "结构迁移 + 素材重混",
    mvpAfterStrong:
      "：复用你上传的视频作为视觉层，并叠加生成的结构、字幕和动态图形。它",
    mvpNot: "不是",
    mvpAfterNot:
      "像素级 VFX 编辑器：不提供人脸滤镜、物体插入、图像修补或妆容迁移。",
    workflowHeading: "演示流程",
    footer:
      "完整链路已接通：上传 -> 分析 -> 结构卡 -> storyboard -> 渲染。支持素材感知的渲染器会在可用时复用上传视频。",
    steps: [
      {
        n: 1,
        title: "上传样例视频",
        description:
          "放入一段短视频。渲染器会把这段素材复用为最终 mp4 的视觉层。",
      },
      {
        n: 2,
        title: "分析视频",
        description:
          "确定性、非 LLM 流程：提取元数据、采样代表帧，并检测场景边界。",
      },
      {
        n: 3,
        title: "提取结构卡",
        description:
          "把可复用的创意结构（开场钩子、节奏、剪辑原子）沉淀成知识库卡片。",
      },
      {
        n: 4,
        title: "生成 Storyboard",
        description:
          "把保存的结构应用到新的创作简报。LLM 会返回可直接渲染的类型化 storyboard JSON。",
      },
      {
        n: 5,
        title: "渲染最终视频",
        description:
          "Remotion 会渲染 storyboard，复用源素材，并叠加生成的字幕、卡片和动态图形。",
      },
    ],
  },
  upload: {
    heading: "上传样例视频",
    description:
      "选择一段竖屏短视频（建议 5-60 秒）。渲染器会把这段素材复用为最终 mp4 的视觉背景。",
    chooseFile: "选择视频",
    fileInputAria: "选择视频文件",
    noFileSelected: "尚未选择文件",
    selectedNotVideo: "选择的文件不是视频。",
    fileTooLarge: (size: string) => `文件超过 200 MB 限制（${size}）。`,
    readyToUpload: "准备上传",
    unknown: "未知",
    upload: "上传",
    uploading: "上传中...",
    reset: "重置",
    limitNote: "最大 200 MB。文件会保留在本机目录",
    emptyState: "还没有选择文件。请选择一个视频来启动流程。",
    uploadFailedStatus: (status: number, message: string) =>
      `上传失败（${status}）：${message}`,
    uploadFailedMessage: (message: string) => `上传失败：${message}`,
    uploadFailedGeneric: "上传失败。",
    success: "上传成功 - 继续第 2 步",
    jobId: "任务 ID",
    filename: "文件名",
    savedPath: "保存路径",
    contentType: "内容类型",
    size: "大小",
    created: "创建时间",
  },
  pipeline: {
    ariaLabel: "流程摘要",
    title: "流程",
    job: "任务",
    waitingForUpload: "等待上传",
    steps: {
      upload: "上传",
      analyze: "分析",
      structureCard: "结构卡",
      storyboard: "Storyboard",
      render: "渲染",
    },
    analysisNote: (scenes: number, frames: number) =>
      `${scenes} 个场景 · ${frames} 帧`,
    storyboardNote: (scenes: number, seconds: number) =>
      `${scenes} 个场景 · ${seconds} 秒`,
    statusLabel: {
      done: "已完成",
      active: "可开始",
      error: "失败",
      pending: "—",
    },
    sourceMediaNone: "源素材：无 · 占位视觉",
    sourceMedia: (parts: string) => `源素材：${parts}`,
    video: "视频",
    frames: (count: number) => `${count} 帧`,
  },
  analyze: {
    heading: "分析视频",
    analyzing: "分析中...",
    rerun: "重新分析",
    run: "分析视频",
    descriptionBeforeJob:
      "确定性、非 LLM 流程：提取元数据、采样代表帧，并切分场景。任务",
    descriptionAfterJob: "。",
    emptyBeforeButton: "点击",
    emptyButton: "分析视频",
    emptyAfterButton: "来提取帧和场景。这会解锁第 3 步。",
    busy: "正在采样帧并检测场景边界...",
    failedStatus: (status: number, message: string) =>
      `分析失败（${status}）：${message}`,
    failedMessage: (message: string) => `分析失败：${message}`,
    failedGeneric: "分析失败。",
    metadata: "元数据",
    duration: "时长",
    fps: "FPS",
    resolution: "分辨率",
    totalFrames: "总帧数",
    fileSize: "文件大小",
    source: "来源",
    frames: "帧",
    noFrames: "未提取到帧。",
    frameAlt: (seconds: string) => `${seconds} 秒处的帧`,
    frameTimestamp: (seconds: string) => `时间 = ${seconds} 秒`,
    scenes: "场景",
    sceneRange: (start: string, end: string) => `${start} 秒 -> ${end} 秒`,
    sceneDuration: (seconds: string) => `（${seconds} 秒）`,
    timeBasedFallback: "按时间兜底切分",
  },
  structure: {
    heading: "提取结构卡",
    extracting: "提取中...",
    reextract: "重新提取结构卡",
    extract: "提取结构卡",
    descriptionBeforeCode:
      "从已分析视频中提炼可复用的创意结构（开场钩子、节奏、原子）。使用当前激活的 LLM provider；如需无 Seed 实时调用测试，请将",
    descriptionBetweenCode: "写入",
    descriptionAfterCode: "。",
    emptyBeforeButton: "点击",
    emptyButton: "提取结构卡",
    emptyAfterButton: "来提炼这次上传的可复用创意模式。",
    busy: "正在调用 LLM 并校验结构卡...",
    failedStatus: (status: number, message: string) =>
      `提取失败（${status}）：${message}`,
    failedMessage: (message: string) => `提取失败：${message}`,
    failedGeneric: "提取失败。",
    pattern: "模式",
    hookType: "开场钩子类型",
    narrativeFlow: "叙事流",
    visualStyle: "视觉风格",
    editingAtoms: (count: number) => `剪辑原子（${count}）`,
    reusableRules: (count: number) => `可复用规则（${count}）`,
    sourceSegments: (count: number) => `来源片段（${count}）`,
    noSegments: "未引用片段。",
    cardId: "结构卡 ID：",
    sourceJob: "来源任务：",
    created: "创建时间：",
  },
  storyboard: {
    heading: "生成 Storyboard",
    description:
      "描述你想让新视频讲什么。LLM 会把提取出的结构应用到你的主题，并输出类型化 storyboard JSON。",
    recommendedPrompts: "推荐演示提示词",
    clickToApply: "点击套用",
    topicBrief: "主题 / 简报",
    placeholder:
      "例如：20 秒奢华香水广告 - 电影感慢揭示、高级氛围、情绪化特写、强视觉钩子。",
    targetDuration: "目标时长（秒）",
    generating: "生成中...",
    regenerate: "重新生成 storyboard",
    generate: "生成 storyboard",
    usesStructureBeforeJob: "使用任务",
    usesStructureAfterJob: "的结构卡。LLM 调用会走当前激活的 provider。",
    emptyBeforeButton: "选择推荐提示词或写下自己的简报，然后点击",
    emptyButton: "生成 storyboard",
    busy: "正在请求 LLM 生成结构化 storyboard，并校验每个场景...",
    promptRequired: "请输入提示词。",
    failedStatus: (status: number, message: string) =>
      `生成失败（${status}）：${message}`,
    failedMessage: (message: string) => `生成失败：${message}`,
    failedGeneric: "生成失败。",
    title: "标题",
    summary: (scenes: number, target: number, actual: string) =>
      `${scenes} 个场景 · 目标 ${target} 秒 · 实际 ${actual} 秒`,
    timelineTitle: (sceneId: string, start: string, end: string) =>
      `${sceneId}：${start} 秒 -> ${end} 秒`,
    sceneTime: (start: string, end: string, duration: string) =>
      `${start} 秒 -> ${end} 秒（${duration} 秒）`,
    storyboardId: "storyboard ID：",
    sourceCards: "来源结构卡：",
    text: "文字",
    quoteText: (text: string) => `“${text}”`,
    visual: "画面",
    assetPrompt: "素材提示词",
    animation: "动画",
    transition: "转场",
    sourceCard: "来源结构卡",
    sourceAtoms: "来源原子",
    prompts: [
      {
        label: "奢华香水广告",
        prompt:
          "基于这段美妆特写视频，创作一个 20 秒奢华香水广告。保留电影感慢揭示、高级氛围、情绪化特写和强视觉钩子，加入优雅字幕、香氛卖点节奏和最终品牌 CTA。",
      },
      {
        label: "护肤品广告",
        prompt:
          "使用这段视频的柔和光线、特写节奏和高级视觉调性，生成一个护肤品广告。重点突出保湿、光泽感和简洁 CTA。",
      },
      {
        label: "AI 编程工具宣传片",
        prompt:
          "沿用这段视频的视觉节奏，创作一个 AI 编程工具短宣传片，把信息替换为生产力、自动化和开发者场景。",
      },
    ],
  },
  render: {
    heading: "渲染最终视频",
    rendering: "渲染中...（请勿关闭此标签页）",
    rerender: "重新渲染视频",
    render: "渲染最终视频",
    storyboard: "Storyboard",
    firstRenderBeforeTime: "首次渲染可能需要",
    firstRenderTime: "60-90 秒",
    firstRenderAfterTime:
      "，因为 Remotion 需要打包项目并预热 Chromium。后续渲染会快很多。",
    mvpNoteBeforeEm:
      "渲染器会复用上传的源视频和提取帧作为视觉背景，并在上层添加生成的字幕、结构和动态图形。当前 MVP",
    mvpNoteEm: "不会",
    mvpNoteAfterEm:
      "执行像素级 VFX 编辑（人脸滤镜、物体合成、图像修补）。",
    status: "状态",
    renderJobId: "渲染任务 ID",
    renderTime: "渲染耗时",
    outputPath: "输出路径",
    mediaUsed: "使用素材",
    directLink: "直接链接：",
    placeholderVisuals: "占位视觉",
    noSourceMedia: "（未关联源素材 - 仅使用渐变背景）",
    sourceVideo: "源视频",
    frames: (count: number) => `${count} 帧`,
    placeholderVisualsLower: "占位视觉",
    job: "任务",
    statusLabels: {
      queued: "排队中",
      running: "运行中",
      succeeded: "成功",
      failed: "失败",
      cancelled: "已取消",
    },
    error404: "服务器上找不到这个 storyboard。请重新生成后再试。",
    error503:
      "Remotion 渲染器尚未安装。请运行 `npm install --workspace apps/renderer` 后重试。",
    error502:
      "渲染子进程失败。请查看 API 日志获取完整 traceback；常见原因包括 Chromium 下载中断或布局异常。",
    failedStatus: (status: number, message: string) =>
      `渲染失败（${status}）：${message}`,
    failedMessage: (message: string) => `渲染失败：${message}`,
    failedUnknown: "渲染失败，原因未知。",
  },
};

const translations: Record<Locale, Copy> = { en, zh };

type LanguageContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  toggleLocale: () => void;
  t: Copy;
};

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocale] = useState<Locale>("en");

  useEffect(() => {
    document.documentElement.lang = localeToHtmlLang(locale);
  }, [locale]);

  const value = useMemo<LanguageContextValue>(
    () => ({
      locale,
      setLocale,
      toggleLocale: () =>
        setLocale((current) => (current === "en" ? "zh" : "en")),
      t: translations[locale],
    }),
    [locale]
  );

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
}

export function localeToHtmlLang(locale: Locale): string {
  return locale === "zh" ? "zh-CN" : "en";
}

export function localeToDateLocale(locale: Locale): string {
  return locale === "zh" ? "zh-CN" : "en-US";
}
