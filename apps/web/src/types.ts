export type Account = {
  id: string;
  label: string;
  email_hint: string | null;
  is_active: boolean;
  has_gpmc_auth_data: boolean;
  has_gptk_cookie_jar: boolean;
  created_at: string;
  updated_at: string;
};

export type Job = {
  id: string;
  account_id: string;
  provider: "gptk" | "gpmc" | "gp_disguise";
  operation: string;
  dry_run: boolean;
  params: Record<string, unknown>;
  status: string;
  progress: number;
  message: string | null;
  result: Record<string, unknown> | null;
  error: Record<string, unknown> | null;
  cancel_requested: boolean;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type OperationCatalogEntry = {
  provider: "gptk" | "gpmc" | "gp_disguise";
  operation: string;
  description: string;
  params_template: Record<string, unknown>;
  destructive: boolean;
  notes: string[];
};
