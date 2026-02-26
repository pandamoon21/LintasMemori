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
