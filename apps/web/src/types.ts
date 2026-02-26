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

export type ExplorerSource = {
  id: string;
  label: string;
  icon: string;
};

export type ExplorerAlbum = {
  media_key: string;
  title: string | null;
  owner_actor_id: string | null;
  item_count: number | null;
  creation_timestamp: number | null;
  modified_timestamp: number | null;
  is_shared: boolean;
  thumb: string | null;
};

export type ExplorerItem = {
  media_key: string;
  dedup_key: string | null;
  timestamp_taken: number | null;
  timestamp_uploaded: number | null;
  file_name: string | null;
  size: number | null;
  type: string | null;
  is_archived: boolean;
  is_favorite: boolean;
  is_trashed: boolean;
  album_ids: string[];
  thumb_url: string | null;
  owner: string | null;
  space_flags: Record<string, unknown>;
  source: string;
};

export type ExplorerItemsResponse = {
  items: ExplorerItem[];
  next_cursor: string | null;
  total_returned: number;
};

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

export type Job = {
  id: string;
  account_id: string;
  provider: string;
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
  events?: JobEvent[];
};

export type JobEvent = {
  id: string;
  job_id: string;
  level: string;
  message: string;
  progress: number | null;
  created_at: string;
};

export type JobStreamEvent = {
  event_id: string;
  type: "job_event" | "job_state";
  job_id: string;
  payload: {
    level: string;
    message: string;
    progress: number | null;
    job: Job;
  };
  created_at: string;
};

export type OperationCatalogEntry = {
  provider: "gptk" | "gpmc" | "gp_disguise";
  operation: string;
  description: string;
  params_template: Record<string, unknown>;
  destructive: boolean;
  notes: string[];
};
