"use client";

import { useState } from "react";

import { AnalyzeCard } from "@/components/AnalyzeCard";
import { UploadCard } from "@/components/UploadCard";

export function WorkflowSection() {
  const [jobId, setJobId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <UploadCard
        onUploaded={(r) => setJobId(r.job_id)}
        onReset={() => setJobId(null)}
      />
      {jobId && <AnalyzeCard jobId={jobId} />}
    </div>
  );
}
