import { useCallback, useState } from "react";

import { postJson } from "../api";
import type { ActionPreviewResult, CommitResponse } from "../types";

export type PreviewDialogState = {
  title: string;
  previewId: string;
  matchCount: number;
  warnings: string[];
  sampleItems: string[];
  commitPath: string;
};

type UploadPreviewResponse = {
  preview_id: string;
  target_count: number;
  sample_files: string[];
  warnings: string[];
};

type PipelinePreviewResponse = {
  preview_id: string;
  input_count: number;
  estimated_outputs: number;
  sample_files: string[];
  warnings: string[];
};

type AdvancedPreviewResponse = {
  preview_id: string;
  operation: string;
  warnings: string[];
};

export function useActionPreviewCommit(onCommitted?: (jobId: string) => Promise<void> | void) {
  const [preview, setPreview] = useState<PreviewDialogState | null>(null);
  const [loading, setLoading] = useState(false);

  const previewAction = useCallback(async (payload: Record<string, unknown>, title: string) => {
    setLoading(true);
    try {
      const response = await postJson<ActionPreviewResult>("/api/v2/actions/preview", payload);
      setPreview({
        title,
        previewId: response.preview_id,
        matchCount: response.match_count,
        warnings: response.warnings,
        sampleItems: response.sample_items.map((item) => item.file_name || item.media_key),
        commitPath: "/api/v2/actions/commit",
      });
      return response;
    } finally {
      setLoading(false);
    }
  }, []);

  const previewUpload = useCallback(async (payload: Record<string, unknown>) => {
    setLoading(true);
    try {
      const response = await postJson<UploadPreviewResponse>("/api/v2/uploads/preview", payload);
      setPreview({
        title: "Preview upload",
        previewId: response.preview_id,
        matchCount: response.target_count,
        warnings: response.warnings,
        sampleItems: response.sample_files,
        commitPath: "/api/v2/uploads/commit",
      });
      return response;
    } finally {
      setLoading(false);
    }
  }, []);

  const previewPipeline = useCallback(async (payload: Record<string, unknown>) => {
    setLoading(true);
    try {
      const response = await postJson<PipelinePreviewResponse>("/api/v2/pipeline/disguise-upload/preview", payload);
      setPreview({
        title: "Preview pipeline disguise -> upload",
        previewId: response.preview_id,
        matchCount: response.estimated_outputs,
        warnings: response.warnings,
        sampleItems: response.sample_files,
        commitPath: "/api/v2/pipeline/disguise-upload/commit",
      });
      return response;
    } finally {
      setLoading(false);
    }
  }, []);

  const previewAdvanced = useCallback(async (payload: Record<string, unknown>) => {
    setLoading(true);
    try {
      const response = await postJson<AdvancedPreviewResponse>("/api/v2/advanced/preview", payload);
      setPreview({
        title: `Preview advanced: ${response.operation}`,
        previewId: response.preview_id,
        matchCount: 1,
        warnings: response.warnings,
        sampleItems: [response.operation],
        commitPath: "/api/v2/advanced/commit",
      });
      return response;
    } finally {
      setLoading(false);
    }
  }, []);

  const closePreview = useCallback(() => {
    setPreview(null);
  }, []);

  const commitPreview = useCallback(async () => {
    if (!preview) {
      throw new Error("No preview to commit");
    }
    setLoading(true);
    try {
      const response = await postJson<CommitResponse>(preview.commitPath, {
        preview_id: preview.previewId,
        confirm: true,
      });
      setPreview(null);
      if (onCommitted) {
        await onCommitted(response.job_id);
      }
      return response;
    } finally {
      setLoading(false);
    }
  }, [preview, onCommitted]);

  return {
    preview,
    loading,
    previewAction,
    previewUpload,
    previewPipeline,
    previewAdvanced,
    closePreview,
    commitPreview,
  };
}
