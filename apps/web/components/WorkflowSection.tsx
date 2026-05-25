"use client";

import { useState } from "react";

import { AnalyzeCard } from "@/components/AnalyzeCard";
import { PipelineSummary } from "@/components/PipelineSummary";
import { RenderStep } from "@/components/RenderStep";
import { StoryboardStep } from "@/components/StoryboardStep";
import { StructureCardStep } from "@/components/StructureCardStep";
import { UploadCard } from "@/components/UploadCard";
import type {
  RenderJob,
  Storyboard,
  StructureCard,
  VideoAnalysis,
  VideoUploadResponse,
} from "@/lib/types";

export function WorkflowSection() {
  const [upload, setUpload] = useState<VideoUploadResponse | null>(null);
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [card, setCard] = useState<StructureCard | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [render, setRender] = useState<RenderJob | null>(null);

  function resetAll() {
    setUpload(null);
    setAnalysis(null);
    setCard(null);
    setStoryboard(null);
    setRender(null);
  }

  const jobId = upload?.job_id ?? null;
  const cardExtracted = !!card;
  const analyzed = !!analysis;

  return (
    <div className="space-y-6">
      <PipelineSummary
        upload={upload}
        analysis={analysis}
        card={card}
        storyboard={storyboard}
        render={render}
      />

      <UploadCard
        onUploaded={(r) => {
          setUpload(r);
          setAnalysis(null);
          setCard(null);
          setStoryboard(null);
          setRender(null);
        }}
        onReset={resetAll}
      />
      {jobId && (
        <AnalyzeCard
          jobId={jobId}
          onAnalyzed={(a) => {
            setAnalysis(a);
            setCard(null);
            setStoryboard(null);
            setRender(null);
          }}
        />
      )}
      {jobId && analyzed && (
        <StructureCardStep
          jobId={jobId}
          onExtracted={(c) => {
            setCard(c);
            setStoryboard(null);
            setRender(null);
          }}
        />
      )}
      {jobId && analyzed && cardExtracted && (
        <StoryboardStep
          jobId={jobId}
          onGenerated={(sb) => {
            setStoryboard(sb);
            setRender(null);
          }}
        />
      )}
      {storyboard && (
        <RenderStep
          storyboardId={storyboard.id}
          storyboardTitle={storyboard.title}
          width={storyboard.width}
          height={storyboard.height}
          onRendered={(rj) => setRender(rj)}
        />
      )}
    </div>
  );
}
