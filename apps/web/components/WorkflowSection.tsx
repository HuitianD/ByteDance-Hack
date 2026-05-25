"use client";

import { useState } from "react";

import { AnalyzeCard } from "@/components/AnalyzeCard";
import { RenderStep } from "@/components/RenderStep";
import { StoryboardStep } from "@/components/StoryboardStep";
import { StructureCardStep } from "@/components/StructureCardStep";
import { UploadCard } from "@/components/UploadCard";
import type { Storyboard } from "@/lib/types";

export function WorkflowSection() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [analyzed, setAnalyzed] = useState(false);
  const [cardExtracted, setCardExtracted] = useState(false);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);

  function reset() {
    setJobId(null);
    setAnalyzed(false);
    setCardExtracted(false);
    setStoryboard(null);
  }

  return (
    <div className="space-y-6">
      <UploadCard
        onUploaded={(r) => {
          setJobId(r.job_id);
          setAnalyzed(false);
          setCardExtracted(false);
          setStoryboard(null);
        }}
        onReset={reset}
      />
      {jobId && (
        <AnalyzeCard
          jobId={jobId}
          onAnalyzed={() => {
            setAnalyzed(true);
            setCardExtracted(false);
            setStoryboard(null);
          }}
        />
      )}
      {jobId && analyzed && (
        <StructureCardStep
          jobId={jobId}
          onExtracted={() => {
            setCardExtracted(true);
            setStoryboard(null);
          }}
        />
      )}
      {jobId && analyzed && cardExtracted && (
        <StoryboardStep
          jobId={jobId}
          onGenerated={(sb) => setStoryboard(sb)}
        />
      )}
      {storyboard && (
        <RenderStep
          storyboardId={storyboard.id}
          storyboardTitle={storyboard.title}
          width={storyboard.width}
          height={storyboard.height}
        />
      )}
    </div>
  );
}
