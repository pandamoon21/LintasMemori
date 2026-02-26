import type { ExplorerItem } from "./explorer";

export type ActionPreviewResult = {
  preview_id: string;
  match_count: number;
  sample_items: ExplorerItem[];
  warnings: string[];
  requires_confirm: boolean;
};

export type CommitResponse = {
  preview_id: string;
  job_id: string;
  status: string;
};

export type OperationCatalogEntry = {
  provider: "gptk" | "gpmc" | "gp_disguise";
  operation: string;
  description: string;
  params_template: Record<string, unknown>;
  destructive: boolean;
  notes: string[];
};
