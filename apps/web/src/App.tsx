import { FormEvent, useEffect, useMemo, useState } from "react";

import { API_BASE_URL, getJson, postForm, postJson } from "./api";
import type { Account, Job, OperationCatalogEntry } from "./types";

const initialJobParams = JSON.stringify(
  {
    target: ".",
    recursive: false,
  },
  null,
  2
);

export function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [catalog, setCatalog] = useState<OperationCatalogEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [accountLabel, setAccountLabel] = useState("");
  const [emailHint, setEmailHint] = useState("");

  const [authAccountId, setAuthAccountId] = useState("");
  const [authData, setAuthData] = useState("");

  const [cookieAccountId, setCookieAccountId] = useState("");
  const [cookieFile, setCookieFile] = useState<File | null>(null);

  const [jobAccountId, setJobAccountId] = useState("");
  const [provider, setProvider] = useState<"gptk" | "gpmc" | "gp_disguise">("gpmc");
  const [operation, setOperation] = useState("gpmc.upload");
  const [paramsText, setParamsText] = useState(initialJobParams);
  const [dryRun, setDryRun] = useState(true);

  const runningCount = useMemo(() => jobs.filter((job) => job.status === "running").length, [jobs]);
  const queuedCount = useMemo(() => jobs.filter((job) => job.status === "queued").length, [jobs]);

  const filteredCatalog = useMemo(() => catalog.filter((entry) => entry.provider === provider), [catalog, provider]);
  const selectedCatalog = useMemo(
    () => catalog.find((entry) => entry.operation === operation) ?? null,
    [catalog, operation]
  );

  async function refreshAll() {
    try {
      const [nextAccounts, nextJobs, nextCatalog] = await Promise.all([
        getJson<Account[]>("/api/accounts"),
        getJson<Job[]>("/api/jobs?limit=200"),
        getJson<OperationCatalogEntry[]>("/api/operations/catalog"),
      ]);
      setAccounts(nextAccounts);
      setJobs(nextJobs);
      setCatalog(nextCatalog);

      if (!authAccountId && nextAccounts[0]) {
        setAuthAccountId(nextAccounts[0].id);
        setCookieAccountId(nextAccounts[0].id);
        setJobAccountId(nextAccounts[0].id);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  useEffect(() => {
    void refreshAll();
    const timer = window.setInterval(() => {
      void refreshAll();
    }, 2500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!filteredCatalog.length) {
      return;
    }
    const operationExists = filteredCatalog.some((entry) => entry.operation === operation);
    if (!operationExists) {
      setOperation(filteredCatalog[0].operation);
      setParamsText(JSON.stringify(filteredCatalog[0].params_template, null, 2));
    }
  }, [provider, filteredCatalog, operation]);

  useEffect(() => {
    const stream = new EventSource(`${API_BASE_URL}/api/jobs/stream`);
    stream.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data) as Job;
        setJobs((prev) => {
          const found = prev.find((item) => item.id === incoming.id);
          if (!found) {
            return [incoming, ...prev];
          }
          return prev.map((item) => (item.id === incoming.id ? incoming : item));
        });
      } catch {
        // ignore parse errors
      }
    };
    stream.onerror = () => {
      stream.close();
    };
    return () => stream.close();
  }, []);

  async function handleCreateAccount(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await postJson<Account>("/api/accounts", {
        label: accountLabel,
        email_hint: emailHint || null,
      });
      setAccountLabel("");
      setEmailHint("");
      await refreshAll();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSetGpmcAuth(event: FormEvent) {
    event.preventDefault();
    if (!authAccountId || !authData) return;
    setBusy(true);
    setError(null);
    try {
      await postJson<Account>(`/api/accounts/${authAccountId}/gpmc-auth`, {
        auth_data: authData,
      });
      setAuthData("");
      await refreshAll();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleImportCookies(event: FormEvent) {
    event.preventDefault();
    if (!cookieAccountId || !cookieFile) return;
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("file", cookieFile);
      await postForm(`/api/accounts/${cookieAccountId}/gptk-cookies/import`, form);
      setCookieFile(null);
      await refreshAll();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function loadTemplate() {
    if (!selectedCatalog) {
      return;
    }
    setParamsText(JSON.stringify(selectedCatalog.params_template, null, 2));
  }

  function addConfirmedFlag() {
    try {
      const parsed = JSON.parse(paramsText) as Record<string, unknown>;
      parsed.confirmed = true;
      setParamsText(JSON.stringify(parsed, null, 2));
    } catch {
      setError("Params JSON is invalid.");
    }
  }

  async function handleCreateJob(event: FormEvent) {
    event.preventDefault();
    if (!jobAccountId) return;

    setBusy(true);
    setError(null);
    try {
      const parsed = JSON.parse(paramsText);
      await postJson<Job>("/api/jobs", {
        account_id: jobAccountId,
        provider,
        operation,
        params: parsed,
        dry_run: dryRun,
      });
      await refreshAll();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function cancelJob(jobId: string) {
    setBusy(true);
    setError(null);
    try {
      await postJson(`/api/jobs/${jobId}/cancel`, {});
      await refreshAll();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <h1>LintasMemori</h1>
        <div className="stats">
          <span>accounts: {accounts.length}</span>
          <span>queued: {queuedCount}</span>
          <span>running: {runningCount}</span>
          <span>operations: {catalog.length}</span>
        </div>
      </header>

      {error ? <div className="error-box">{error}</div> : null}

      <main className="grid">
        <section className="panel">
          <h2>Account Setup</h2>
          <form className="stack" onSubmit={handleCreateAccount}>
            <label>
              Label
              <input
                value={accountLabel}
                onChange={(event) => setAccountLabel(event.target.value)}
                placeholder="Personal Pixel"
                required
              />
            </label>
            <label>
              Email Hint
              <input value={emailHint} onChange={(event) => setEmailHint(event.target.value)} placeholder="optional" />
            </label>
            <button disabled={busy}>Create account</button>
          </form>

          <form className="stack" onSubmit={handleSetGpmcAuth}>
            <h3>Set gpmc auth_data</h3>
            <select value={authAccountId} onChange={(event) => setAuthAccountId(event.target.value)} required>
              <option value="">Select account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.label}
                </option>
              ))}
            </select>
            <textarea
              value={authData}
              onChange={(event) => setAuthData(event.target.value)}
              rows={4}
              placeholder="androidId=...&app=..."
            />
            <button disabled={busy}>Save auth_data</button>
          </form>

          <form className="stack" onSubmit={handleImportCookies}>
            <h3>Import GPTK cookies</h3>
            <select value={cookieAccountId} onChange={(event) => setCookieAccountId(event.target.value)} required>
              <option value="">Select account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.label}
                </option>
              ))}
            </select>
            <input type="file" accept=".txt" onChange={(event) => setCookieFile(event.target.files?.[0] ?? null)} required />
            <button disabled={busy}>Import cookies</button>
          </form>

          <div className="account-table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Label</th>
                  <th>Email</th>
                  <th>gpmc</th>
                  <th>gptk</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((account) => (
                  <tr key={account.id}>
                    <td>{account.label}</td>
                    <td>{account.email_hint || "-"}</td>
                    <td>{account.has_gpmc_auth_data ? "yes" : "no"}</td>
                    <td>{account.has_gptk_cookie_jar ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel wide">
          <h2>Job Queue</h2>

          <form className="stack" onSubmit={handleCreateJob}>
            <div className="row row-5">
              <label>
                Account
                <select value={jobAccountId} onChange={(event) => setJobAccountId(event.target.value)} required>
                  <option value="">Select account</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.label}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Provider
                <select value={provider} onChange={(event) => setProvider(event.target.value as typeof provider)}>
                  <option value="gpmc">gpmc</option>
                  <option value="gptk">gptk</option>
                  <option value="gp_disguise">gp_disguise</option>
                </select>
              </label>

              <label>
                Operation
                <select value={operation} onChange={(event) => setOperation(event.target.value)}>
                  {filteredCatalog.map((entry) => (
                    <option key={entry.operation} value={entry.operation}>
                      {entry.operation}
                    </option>
                  ))}
                </select>
              </label>

              <label className="checkbox-row">
                <input type="checkbox" checked={dryRun} onChange={(event) => setDryRun(event.target.checked)} />
                Dry-run
              </label>

              <div className="stack compact">
                <button type="button" onClick={loadTemplate} disabled={busy || !selectedCatalog}>
                  Load template
                </button>
                {!dryRun && selectedCatalog?.destructive ? (
                  <button type="button" onClick={addConfirmedFlag} disabled={busy}>
                    Add confirmed=true
                  </button>
                ) : null}
              </div>
            </div>

            {selectedCatalog ? (
              <div className="meta-box">
                <div>{selectedCatalog.description}</div>
                {selectedCatalog.destructive ? <div className="warn-text">Destructive operation: run dry-run first.</div> : null}
                {selectedCatalog.notes.map((note) => (
                  <div key={note} className="note-text">
                    {note}
                  </div>
                ))}
              </div>
            ) : null}

            <label>
              Params JSON
              <textarea value={paramsText} onChange={(event) => setParamsText(event.target.value)} rows={10} />
            </label>
            <button disabled={busy}>Submit job</button>
          </form>

          <div className="jobs-wrapper">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Provider</th>
                  <th>Operation</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Message</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="mono">{job.id.slice(0, 8)}</td>
                    <td>{job.provider}</td>
                    <td className="mono">{job.operation}</td>
                    <td>{job.status}</td>
                    <td>{Math.round(job.progress * 100)}%</td>
                    <td>{job.message || "-"}</td>
                    <td>
                      {job.status === "queued" || job.status === "running" ? (
                        <button className="danger" onClick={() => void cancelJob(job.id)} type="button">
                          cancel
                        </button>
                      ) : (
                        <span>-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
