import type { Job } from "../types";

const FINAL_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

type TaskCenterProps = {
  jobs: Job[];
  activeCount: number;
  onCancel: (jobId: string) => void;
  busy: boolean;
};

function progressPercent(value: number): number {
  const clamped = Math.max(0, Math.min(1, value || 0));
  return Math.round(clamped * 100);
}

export function TaskCenter({ jobs, activeCount, onCancel, busy }: TaskCenterProps) {
  const active = jobs.filter((item) => !FINAL_STATUSES.has(item.status));
  const completed = jobs.filter((item) => FINAL_STATUSES.has(item.status));

  const sections: Array<{ key: string; label: string; rows: Job[] }> = [
    { key: "active", label: `Active (${active.length})`, rows: active },
    { key: "completed", label: `Completed (${completed.length})`, rows: completed },
  ];

  return (
    <aside className="lm-task-center lm-surface lm-panel">
      <h2>Task Center</h2>
      <p className="lm-muted">Active: {activeCount} · Total: {jobs.length}</p>

      <div className="lm-task-list">
        {sections.map((section) => (
          <section key={section.key} className="lm-task-section">
            <h3 className="lm-task-section-title">{section.label}</h3>
            {section.rows.length === 0 ? <div className="lm-muted">No jobs.</div> : null}
            {section.rows.map((job) => {
              const percent = progressPercent(job.progress);
              const canCancel = job.status === "queued" || job.status === "running";
              return (
                <article key={job.id} className="lm-task-card">
                  <div className="lm-task-top">
                    <strong>{job.operation}</strong>
                    <span className={`lm-status ${job.status}`}>{job.status}</span>
                  </div>
                  <div className="lm-task-meta">{job.provider} · {percent}%</div>
                  <div className="lm-progress">
                    <div className="lm-progress-bar" style={{ width: `${percent}%` }} />
                  </div>
                  <div className="lm-task-message">{job.message || "-"}</div>
                  {canCancel ? (
                    <button className="lm-btn-danger" onClick={() => onCancel(job.id)} disabled={busy} type="button">
                      Cancel
                    </button>
                  ) : null}
                </article>
              );
            })}
          </section>
        ))}
      </div>
    </aside>
  );
}
