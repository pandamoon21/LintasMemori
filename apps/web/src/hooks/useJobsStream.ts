import { useCallback, useEffect, useMemo, useState } from "react";

import { API_BASE_URL, getJson, postJson } from "../api";
import type { Job, JobStreamEvent } from "../types";

function mergeJob(list: Job[], incoming: Job): Job[] {
  const idx = list.findIndex((item) => item.id === incoming.id);
  if (idx === -1) {
    return [incoming, ...list];
  }
  const next = [...list];
  next[idx] = incoming;
  return next;
}

function rankStatus(status: string): number {
  if (status === "running") return 0;
  if (status === "queued") return 1;
  if (status === "requires_credentials") return 2;
  if (status === "failed") return 3;
  if (status === "cancelled") return 4;
  return 5;
}

export function useJobsStream(activeAccountId: string) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshJobs = useCallback(async (limit: number = 240) => {
    setLoading(true);
    try {
      const rows = await getJson<Job[]>(`/api/v2/jobs?limit=${limit}`);
      setJobs(rows);
      return rows;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelJob = useCallback(async (jobId: string) => {
    await postJson(`/api/v2/jobs/${jobId}/cancel`, {});
    await refreshJobs();
  }, [refreshJobs]);

  useEffect(() => {
    void refreshJobs();
    const timer = window.setInterval(() => {
      void refreshJobs().catch(() => undefined);
    }, 8000);
    return () => window.clearInterval(timer);
  }, [refreshJobs]);

  useEffect(() => {
    let closed = false;
    let retry = 0;
    let stream: EventSource | null = null;
    let retryTimer: number | null = null;

    const connect = () => {
      if (closed) return;
      stream = new EventSource(`${API_BASE_URL}/api/v2/jobs/stream`);

      stream.onopen = () => {
        retry = 0;
      };

      stream.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data) as JobStreamEvent;
          const incoming = payload.payload.job;
          setJobs((prev) => mergeJob(prev, incoming));
        } catch {
          // ignore malformed SSE payload
        }
      };

      stream.onerror = () => {
        if (stream) {
          stream.close();
          stream = null;
        }
        if (closed) return;
        const delayMs = Math.min(12000, 1000 * 2 ** retry);
        retry = Math.min(retry + 1, 6);
        retryTimer = window.setTimeout(() => {
          connect();
        }, delayMs);
      };
    };

    connect();

    return () => {
      closed = true;
      if (stream) stream.close();
      if (retryTimer !== null) window.clearTimeout(retryTimer);
    };
  }, []);

  const filteredJobs = useMemo(() => {
    const scoped = activeAccountId ? jobs.filter((item) => item.account_id === activeAccountId) : jobs;
    return scoped
      .slice()
      .sort((a, b) => {
        const rank = rankStatus(a.status) - rankStatus(b.status);
        if (rank !== 0) return rank;
        return (b.updated_at || "").localeCompare(a.updated_at || "");
      });
  }, [jobs, activeAccountId]);

  const activeCount = useMemo(
    () => filteredJobs.filter((item) => item.status === "running" || item.status === "queued").length,
    [filteredJobs]
  );

  return {
    jobs: filteredJobs,
    allJobs: jobs,
    activeCount,
    loading,
    refreshJobs,
    cancelJob,
  };
}
