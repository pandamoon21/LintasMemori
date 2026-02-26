import type { Account } from "../types";
import type { DrawerKey } from "../hooks/useDrawers";

type TopBarProps = {
  accounts: Account[];
  activeAccountId: string;
  onAccountChange: (accountId: string) => void;
  onRefreshIndex: () => void;
  onToggleDrawer: (drawer: Exclude<DrawerKey, null>) => void;
  busy: boolean;
  activeJobs: number;
};

export function TopBar({
  accounts,
  activeAccountId,
  onAccountChange,
  onRefreshIndex,
  onToggleDrawer,
  busy,
  activeJobs,
}: TopBarProps) {
  return (
    <header className="lm-topbar lm-surface">
      <div className="lm-brand">
        <h1>LintasMemori</h1>
        <p>Google-like organizer dashboard for Google Photos workflows</p>
      </div>

      <div className="lm-topbar-actions">
        <label className="lm-field">
          <span>Account</span>
          <select value={activeAccountId} onChange={(event) => onAccountChange(event.target.value)}>
            <option value="">Select account</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.label}
              </option>
            ))}
          </select>
        </label>

        <button onClick={onRefreshIndex} disabled={busy || !activeAccountId}>
          Refresh Index
        </button>

        <button className="lm-btn-ghost" onClick={() => onToggleDrawer("setup")}>Setup</button>
        <button className="lm-btn-ghost" onClick={() => onToggleDrawer("upload")}>Upload</button>
        <button className="lm-btn-ghost" onClick={() => onToggleDrawer("pipeline")}>Pipeline</button>
        <button className="lm-btn-ghost" onClick={() => onToggleDrawer("advanced")}>Advanced</button>

        <div className="lm-chip">Active jobs: {activeJobs}</div>
      </div>
    </header>
  );
}
