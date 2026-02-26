import { FormEvent, useEffect, useMemo, useState } from "react";

import { API_BASE_URL, getJson, postForm, postJson } from "./api";
import type {
  Account,
  ActionPreviewResult,
  CommitResponse,
  ExplorerAlbum,
  ExplorerItem,
  ExplorerItemsResponse,
  ExplorerSource,
  Job,
  JobStreamEvent,
  OperationCatalogEntry,
} from "./types";

type PreviewDialog = {
  title: string;
  previewId: string;
  matchCount: number;
  warnings: string[];
  sampleItems: string[];
  commitPath: string;
};

const defaultActionDate = new Date().toISOString().slice(0, 16);

function timestampLabel(timestamp: number | null): string {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
}

function bytesLabel(size: number | null): string {
  if (!size || size <= 0) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

export function App() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [sources, setSources] = useState<ExplorerSource[]>([]);
  const [albums, setAlbums] = useState<ExplorerAlbum[]>([]);
  const [items, setItems] = useState<ExplorerItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [operations, setOperations] = useState<OperationCatalogEntry[]>([]);

  const [activeAccountId, setActiveAccountId] = useState("");
  const [activeSource, setActiveSource] = useState("library");
  const [activeAlbumId, setActiveAlbumId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterFavorite, setFilterFavorite] = useState<boolean | null>(null);
  const [filterArchived, setFilterArchived] = useState<boolean | null>(null);
  const [pageCursor, setPageCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [selectedDateTime, setSelectedDateTime] = useState(defaultActionDate);

  const [previewDialog, setPreviewDialog] = useState<PreviewDialog | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [showSetup, setShowSetup] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showPipeline, setShowPipeline] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  const [newAccountLabel, setNewAccountLabel] = useState("");
  const [newAccountEmail, setNewAccountEmail] = useState("");
  const [gpmcAuthData, setGpmcAuthData] = useState("");
  const [cookieText, setCookieText] = useState("");
  const [cookieFile, setCookieFile] = useState<File | null>(null);

  const [uploadTarget, setUploadTarget] = useState(".");
  const [uploadAlbumName, setUploadAlbumName] = useState("");
  const [uploadRecursive, setUploadRecursive] = useState(false);

  const [advancedProvider, setAdvancedProvider] = useState<"gptk" | "gpmc" | "gp_disguise">("gptk");
  const [advancedOperation, setAdvancedOperation] = useState("");
  const [advancedParamsText, setAdvancedParamsText] = useState("{}");

  const [pipelineInputText, setPipelineInputText] = useState("");
  const [pipelineDisguiseType, setPipelineDisguiseType] = useState<"image" | "video">("image");
  const [pipelineSeparator, setPipelineSeparator] = useState("FILE_DATA_BEGIN");
  const [pipelineKeepArtifacts, setPipelineKeepArtifacts] = useState(false);
  const [pipelineOutputDir, setPipelineOutputDir] = useState("");
  const [pipelineAlbumName, setPipelineAlbumName] = useState("");

  const activeAccount = useMemo(() => accounts.find((item) => item.id === activeAccountId) ?? null, [accounts, activeAccountId]);
  const selectedCount = selectedKeys.size;
  const activeJobs = useMemo(() => jobs.filter((item) => item.status === "running" || item.status === "queued").length, [jobs]);

  const providerOperations = useMemo(
    () => operations.filter((item) => item.provider === advancedProvider),
    [operations, advancedProvider]
  );

  function buildItemQuery(cursor?: string | null): string {
    const params = new URLSearchParams();
    params.set("account_id", activeAccountId);
    params.set("page_size", "160");
    if (cursor) params.set("page_cursor", cursor);
    if (activeSource !== "albums") {
      params.set("source", activeSource);
    }
    if (activeAlbumId) params.set("album_id", activeAlbumId);
    if (search.trim()) params.set("search", search.trim());
    if (filterFavorite !== null) params.set("favorite", String(filterFavorite));
    if (filterArchived !== null) params.set("archived", String(filterArchived));
    return `/api/v2/explorer/items?${params.toString()}`;
  }

  async function loadBootstrap() {
    try {
      const [accountRows, sourceRows, opRows, jobRows] = await Promise.all([
        getJson<Account[]>("/api/v2/accounts"),
        getJson<ExplorerSource[]>("/api/v2/explorer/sources"),
        getJson<OperationCatalogEntry[]>("/api/v2/advanced/operations"),
        getJson<Job[]>("/api/v2/jobs?limit=120"),
      ]);
      setAccounts(accountRows);
      setSources(sourceRows);
      setOperations(opRows);
      setJobs(jobRows);
      if (!activeAccountId && accountRows[0]) setActiveAccountId(accountRows[0].id);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function loadAlbums() {
    if (!activeAccountId) return;
    const rows = await getJson<ExplorerAlbum[]>(`/api/v2/explorer/albums?account_id=${activeAccountId}`);
    setAlbums(rows);
  }

  async function loadItems(reset = true) {
    if (!activeAccountId) return;
    const cursor = reset ? null : nextCursor;
    if (!reset && !cursor) return;
    const rows = await getJson<ExplorerItemsResponse>(buildItemQuery(cursor));
    setItems((prev) => (reset ? rows.items : [...prev, ...rows.items]));
    setPageCursor(cursor);
    setNextCursor(rows.next_cursor);
    if (reset) setSelectedKeys(new Set());
  }

  async function loadJobs() {
    const rows = await getJson<Job[]>("/api/v2/jobs?limit=200");
    setJobs(rows);
  }

  useEffect(() => {
    void loadBootstrap();
    const timer = window.setInterval(() => {
      void loadJobs().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!providerOperations.length) return;
    if (!providerOperations.find((item) => item.operation === advancedOperation)) {
      const next = providerOperations[0];
      setAdvancedOperation(next.operation);
      setAdvancedParamsText(JSON.stringify(next.params_template, null, 2));
    }
  }, [providerOperations, advancedOperation]);

  useEffect(() => {
    if (!activeAccountId) return;
    setError(null);
    void loadAlbums().catch((err) => setError((err as Error).message));
    void loadItems(true).catch((err) => setError((err as Error).message));
  }, [activeAccountId, activeSource, activeAlbumId, search, filterFavorite, filterArchived]);

  useEffect(() => {
    const stream = new EventSource(`${API_BASE_URL}/api/v2/jobs/stream`);
    stream.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as JobStreamEvent;
        const incoming = payload.payload.job;
        setJobs((prev) => {
          const idx = prev.findIndex((item) => item.id === incoming.id);
          if (idx === -1) return [incoming, ...prev];
          const next = [...prev];
          next[idx] = incoming;
          return next;
        });
      } catch {
        // ignore malformed event
      }
    };
    stream.onerror = () => stream.close();
    return () => stream.close();
  }, []);

  function resetStatus() {
    setError(null);
    setMessage(null);
  }

  async function refreshIndex() {
    if (!activeAccountId) return;
    resetStatus();
    setBusy(true);
    try {
      await postJson("/api/v2/explorer/index/refresh", {
        account_id: activeAccountId,
        max_items: 5000,
        include_album_members: true,
        force_full: false,
      });
      setMessage("Explorer index refresh queued.");
      await loadJobs();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function createAccount(event: FormEvent) {
    event.preventDefault();
    if (!newAccountLabel.trim()) return;
    resetStatus();
    setBusy(true);
    try {
      const created = await postJson<Account>("/api/v2/accounts", {
        label: newAccountLabel.trim(),
        email_hint: newAccountEmail.trim() || null,
      });
      setNewAccountLabel("");
      setNewAccountEmail("");
      await loadBootstrap();
      setActiveAccountId(created.id);
      setMessage("Account created.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveGpmcAuth(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId || !gpmcAuthData.trim()) return;
    resetStatus();
    setBusy(true);
    try {
      await postJson(`/api/v2/accounts/${activeAccountId}/credentials/gpmc`, {
        auth_data: gpmcAuthData.trim(),
      });
      setGpmcAuthData("");
      await loadBootstrap();
      setMessage("gpmc credentials saved.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function pasteCookies(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId || !cookieText.trim()) return;
    resetStatus();
    setBusy(true);
    try {
      await postJson(`/api/v2/accounts/${activeAccountId}/credentials/cookies/paste`, {
        cookie_string: cookieText.trim(),
      });
      setCookieText("");
      await loadBootstrap();
      setMessage("Cookie string imported.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function importCookieFile(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId || !cookieFile) return;
    resetStatus();
    setBusy(true);
    try {
      const form = new FormData();
      form.set("file", cookieFile);
      await postForm(`/api/v2/accounts/${activeAccountId}/credentials/cookies/import`, form);
      setCookieFile(null);
      await loadBootstrap();
      setMessage("Cookie file imported.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function refreshSession() {
    if (!activeAccountId) return;
    resetStatus();
    setBusy(true);
    try {
      await postJson(`/api/v2/accounts/${activeAccountId}/session/refresh`, { source_path: "/" });
      setMessage("Session refreshed from cookies.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function toggleSelected(mediaKey: string) {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(mediaKey)) next.delete(mediaKey);
      else next.add(mediaKey);
      return next;
    });
  }

  async function previewAction(action: string, actionParams: Record<string, unknown> = {}) {
    if (!activeAccountId) return;
    resetStatus();
    setBusy(true);
    try {
      const payload =
        selectedKeys.size > 0
          ? {
              account_id: activeAccountId,
              selected_media_keys: Array.from(selectedKeys),
              action,
              action_params: actionParams,
            }
          : {
              account_id: activeAccountId,
              query: {
                source: activeSource !== "albums" ? activeSource : undefined,
                album_id: activeAlbumId || undefined,
                search: search.trim() || undefined,
                favorite: filterFavorite ?? undefined,
                archived: filterArchived ?? undefined,
                page_size: 500,
              },
              action,
              action_params: actionParams,
            };

      const preview = await postJson<ActionPreviewResult>("/api/v2/actions/preview", payload);
      setPreviewDialog({
        title: `Preview action: ${action}`,
        previewId: preview.preview_id,
        matchCount: preview.match_count,
        warnings: preview.warnings,
        sampleItems: preview.sample_items.map((item) => item.file_name || item.media_key),
        commitPath: "/api/v2/actions/commit",
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function openUploadPreview(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId || !uploadTarget.trim()) return;
    resetStatus();
    setBusy(true);
    try {
      const preview = await postJson<{
        preview_id: string;
        target_count: number;
        sample_files: string[];
        warnings: string[];
      }>("/api/v2/uploads/preview", {
        account_id: activeAccountId,
        target: uploadTarget,
        recursive: uploadRecursive,
        gpmc_upload_options: {
          album_name: uploadAlbumName.trim() || undefined,
        },
      });
      setPreviewDialog({
        title: "Preview upload",
        previewId: preview.preview_id,
        matchCount: preview.target_count,
        warnings: preview.warnings,
        sampleItems: preview.sample_files,
        commitPath: "/api/v2/uploads/commit",
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function openPipelinePreview(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId) return;
    const inputFiles = pipelineInputText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
    if (!inputFiles.length) return;
    resetStatus();
    setBusy(true);
    try {
      const preview = await postJson<{
        preview_id: string;
        input_count: number;
        estimated_outputs: number;
        sample_files: string[];
        warnings: string[];
      }>("/api/v2/pipeline/disguise-upload/preview", {
        account_id: activeAccountId,
        input_files: inputFiles,
        disguise_type: pipelineDisguiseType,
        separator: pipelineSeparator,
        output_policy: {
          keep_artifacts: pipelineKeepArtifacts,
          output_dir: pipelineOutputDir.trim() || undefined,
        },
        gpmc_upload_options: {
          album_name: pipelineAlbumName.trim() || undefined,
        },
      });
      setPreviewDialog({
        title: "Preview pipeline disguise -> upload",
        previewId: preview.preview_id,
        matchCount: preview.estimated_outputs,
        warnings: preview.warnings,
        sampleItems: preview.sample_files,
        commitPath: "/api/v2/pipeline/disguise-upload/commit",
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function openAdvancedPreview(event: FormEvent) {
    event.preventDefault();
    if (!activeAccountId || !advancedOperation) return;
    resetStatus();
    setBusy(true);
    try {
      const params = JSON.parse(advancedParamsText) as Record<string, unknown>;
      const preview = await postJson<{
        preview_id: string;
        operation: string;
        warnings: string[];
      }>("/api/v2/advanced/preview", {
        account_id: activeAccountId,
        provider: advancedProvider,
        operation: advancedOperation,
        params,
      });
      setPreviewDialog({
        title: `Preview advanced: ${preview.operation}`,
        previewId: preview.preview_id,
        matchCount: 1,
        warnings: preview.warnings,
        sampleItems: [preview.operation],
        commitPath: "/api/v2/advanced/commit",
      });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function commitPreview() {
    if (!previewDialog) return;
    resetStatus();
    setBusy(true);
    try {
      await postJson<CommitResponse>(previewDialog.commitPath, {
        preview_id: previewDialog.previewId,
        confirm: true,
      });
      setPreviewDialog(null);
      setMessage("Commit queued as async job.");
      await Promise.all([loadJobs(), loadItems(true)]);
      setSelectedKeys(new Set());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function cancelJob(jobId: string) {
    resetStatus();
    setBusy(true);
    try {
      await postJson(`/api/v2/jobs/${jobId}/cancel`, {});
      await loadJobs();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function runAddAlbum() {
    const raw = window.prompt("Masukkan album_id atau ketik name:NamaAlbum");
    if (!raw) return;
    if (raw.startsWith("name:")) {
      await previewAction("add_album", { album_name: raw.slice(5).trim() });
      return;
    }
    await previewAction("add_album", { album_id: raw.trim() });
  }

  async function runRemoveAlbum() {
    const albumId = activeAlbumId || window.prompt("Masukkan album_id untuk remove") || "";
    if (!albumId.trim()) return;
    await previewAction("remove_album", { album_id: albumId.trim() });
  }

  async function runSetDateTime() {
    const date = new Date(selectedDateTime);
    if (Number.isNaN(date.getTime())) {
      setError("Invalid date/time format");
      return;
    }
    const timezoneSec = -date.getTimezoneOffset() * 60;
    await previewAction("set_datetime", {
      timestamp_sec: Math.floor(date.getTime() / 1000),
      timezone_sec: timezoneSec,
    });
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <h1>LintasMemori Dashboard</h1>
          <p>Native Python backend for organizer + upload + disguise pipeline</p>
        </div>

        <div className="topbar-actions">
          <label>
            Account
            <select value={activeAccountId} onChange={(event) => setActiveAccountId(event.target.value)}>
              <option value="">Select account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.label}
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => void refreshIndex()} disabled={busy || !activeAccountId}>
            Refresh Index
          </button>
          <button onClick={() => setShowSetup((prev) => !prev)} className="ghost">
            Setup
          </button>
          <button onClick={() => setShowUpload((prev) => !prev)} className="ghost">
            Upload
          </button>
          <button onClick={() => setShowPipeline((prev) => !prev)} className="ghost">
            Pipeline
          </button>
          <button onClick={() => setShowAdvanced((prev) => !prev)} className="ghost">
            Advanced
          </button>
        </div>
      </header>

      {error ? <div className="notice error">{error}</div> : null}
      {message ? <div className="notice info">{message}</div> : null}

      <div className="layout">
        <aside className="sidebar">
          <section className="card">
            <h2>Sources</h2>
            <div className="source-list">
              {sources.map((source) => (
                <button
                  key={source.id}
                  className={activeSource === source.id && !activeAlbumId ? "source active" : "source"}
                  onClick={() => {
                    setActiveSource(source.id);
                    setActiveAlbumId(null);
                  }}
                >
                  {source.label}
                </button>
              ))}
            </div>
          </section>

          <section className="card">
            <h2>Albums</h2>
            <div className="album-list">
              {albums.map((album) => (
                <button
                  key={album.media_key}
                  className={activeAlbumId === album.media_key ? "album active" : "album"}
                  onClick={() => {
                    setActiveSource("albums");
                    setActiveAlbumId(album.media_key);
                  }}
                >
                  <span>{album.title || album.media_key.slice(0, 8)}</span>
                  <small>{album.item_count ?? 0}</small>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <main className="explorer">
          <section className="toolbar card">
            <div className="search-row">
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by filename/media key"
              />
              <button className={filterFavorite === true ? "chip active" : "chip"} onClick={() => setFilterFavorite((prev) => (prev === true ? null : true))}>
                Favorite
              </button>
              <button className={filterArchived === true ? "chip active" : "chip"} onClick={() => setFilterArchived((prev) => (prev === true ? null : true))}>
                Archived
              </button>
              <button onClick={() => void loadItems(true)} className="ghost">
                Refresh
              </button>
            </div>

            <div className="action-row">
              <span>{items.length} items loaded</span>
              <span>{selectedCount} selected</span>
              <button onClick={() => void previewAction("trash")} disabled={busy || !activeAccountId}>
                Trash
              </button>
              <button onClick={() => void previewAction("restore")} disabled={busy || !activeAccountId}>
                Restore
              </button>
              <button onClick={() => void previewAction("archive")} disabled={busy || !activeAccountId}>
                Archive
              </button>
              <button onClick={() => void previewAction("unarchive")} disabled={busy || !activeAccountId}>
                Unarchive
              </button>
              <button onClick={() => void previewAction("favorite")} disabled={busy || !activeAccountId}>
                Favorite
              </button>
              <button onClick={() => void previewAction("unfavorite")} disabled={busy || !activeAccountId}>
                Unfavorite
              </button>
              <button onClick={() => void runAddAlbum()} disabled={busy || !activeAccountId}>
                Add Album
              </button>
              <button onClick={() => void runRemoveAlbum()} disabled={busy || !activeAccountId}>
                Remove Album
              </button>
              <input type="datetime-local" value={selectedDateTime} onChange={(event) => setSelectedDateTime(event.target.value)} />
              <button onClick={() => void runSetDateTime()} disabled={busy || !activeAccountId}>
                Set Date
              </button>
            </div>
          </section>

          <section className="grid card">
            {items.map((item) => (
              <article
                key={item.media_key}
                className={selectedKeys.has(item.media_key) ? "media-card selected" : "media-card"}
                onClick={() => toggleSelected(item.media_key)}
              >
                <div className="thumb">{item.thumb_url ? <img src={item.thumb_url} alt={item.file_name || item.media_key} /> : <span>No preview</span>}</div>
                <div className="meta">
                  <h3>{item.file_name || item.media_key}</h3>
                  <p>{timestampLabel(item.timestamp_taken)}</p>
                  <p>
                    {item.type || "-"} · {bytesLabel(item.size)}
                  </p>
                  <div className="flags">
                    {item.is_trashed ? <span>Trash</span> : null}
                    {item.is_archived ? <span>Archived</span> : null}
                    {item.is_favorite ? <span>Favorite</span> : null}
                  </div>
                </div>
              </article>
            ))}
            {!items.length ? <div className="empty">No items found in current query.</div> : null}
          </section>

          <div className="footer-row">
            <button onClick={() => void loadItems(false)} disabled={!nextCursor || busy}>
              Load More
            </button>
            <span>cursor: {pageCursor || "-"}</span>
          </div>
        </main>

        <aside className="tasks card">
          <h2>Task Center</h2>
          <p>
            Active jobs: {activeJobs} · Total: {jobs.length}
          </p>
          <div className="jobs">
            {jobs.map((job) => (
              <div key={job.id} className="job">
                <div className="job-top">
                  <strong>{job.operation}</strong>
                  <span>{job.status}</span>
                </div>
                <small>
                  {job.provider} · {Math.round(job.progress * 100)}%
                </small>
                <small>{job.message || "-"}</small>
                {(job.status === "queued" || job.status === "running") && (
                  <button onClick={() => void cancelJob(job.id)} className="danger">
                    Cancel
                  </button>
                )}
              </div>
            ))}
          </div>
        </aside>
      </div>

      {showSetup && (
        <section className="drawer card">
          <h2>Account Setup</h2>
          <p>{activeAccount ? `${activeAccount.label} selected` : "No account selected"}</p>

          <form onSubmit={createAccount} className="stack">
            <h3>Create account</h3>
            <input value={newAccountLabel} onChange={(event) => setNewAccountLabel(event.target.value)} placeholder="Account label" required />
            <input value={newAccountEmail} onChange={(event) => setNewAccountEmail(event.target.value)} placeholder="Email hint (optional)" />
            <button disabled={busy}>Create</button>
          </form>

          <form onSubmit={saveGpmcAuth} className="stack">
            <h3>Set gpmc auth_data</h3>
            <textarea
              value={gpmcAuthData}
              onChange={(event) => setGpmcAuthData(event.target.value)}
              placeholder="androidId=...&app=..."
              rows={3}
              required
            />
            <button disabled={busy || !activeAccountId}>Save gpmc auth</button>
          </form>

          <form onSubmit={pasteCookies} className="stack">
            <h3>Paste cookie string</h3>
            <textarea value={cookieText} onChange={(event) => setCookieText(event.target.value)} placeholder="SAPISID=...; HSID=...;" rows={3} required />
            <button disabled={busy || !activeAccountId}>Import cookies (paste)</button>
          </form>

          <form onSubmit={importCookieFile} className="stack">
            <h3>Import cookie file</h3>
            <input type="file" accept=".txt" onChange={(event) => setCookieFile(event.target.files?.[0] ?? null)} required />
            <button disabled={busy || !activeAccountId}>Import file</button>
          </form>

          <button onClick={() => void refreshSession()} disabled={busy || !activeAccountId}>
            Refresh GPTK session
          </button>
        </section>
      )}

      {showUpload && (
        <section className="drawer card">
          <h2>Upload Wizard</h2>
          <form onSubmit={openUploadPreview} className="stack">
            <input value={uploadTarget} onChange={(event) => setUploadTarget(event.target.value)} placeholder="File/folder path" required />
            <input value={uploadAlbumName} onChange={(event) => setUploadAlbumName(event.target.value)} placeholder="Album name (optional)" />
            <label className="toggle">
              <input type="checkbox" checked={uploadRecursive} onChange={(event) => setUploadRecursive(event.target.checked)} />
              Recursive scan
            </label>
            <button disabled={busy || !activeAccountId}>Preview upload</button>
          </form>
        </section>
      )}

      {showPipeline && (
        <section className="drawer card">
          <h2>Pipeline Wizard: disguise -&gt; upload</h2>
          <form onSubmit={openPipelinePreview} className="stack">
            <textarea
              value={pipelineInputText}
              onChange={(event) => setPipelineInputText(event.target.value)}
              placeholder="One file/folder/pattern per line"
              rows={4}
              required
            />
            <label>
              Disguise type
              <select value={pipelineDisguiseType} onChange={(event) => setPipelineDisguiseType(event.target.value as "image" | "video")}>
                <option value="image">image</option>
                <option value="video">video</option>
              </select>
            </label>
            <input value={pipelineSeparator} onChange={(event) => setPipelineSeparator(event.target.value)} placeholder="Separator" />
            <input value={pipelineOutputDir} onChange={(event) => setPipelineOutputDir(event.target.value)} placeholder="Output dir (optional)" />
            <input value={pipelineAlbumName} onChange={(event) => setPipelineAlbumName(event.target.value)} placeholder="Upload album (optional)" />
            <label className="toggle">
              <input type="checkbox" checked={pipelineKeepArtifacts} onChange={(event) => setPipelineKeepArtifacts(event.target.checked)} />
              Keep artifacts after upload
            </label>
            <button disabled={busy || !activeAccountId}>Preview pipeline</button>
          </form>
        </section>
      )}

      {showAdvanced && (
        <section className="drawer card">
          <h2>Advanced Drawer</h2>
          <form onSubmit={openAdvancedPreview} className="stack">
            <label>
              Provider
              <select value={advancedProvider} onChange={(event) => setAdvancedProvider(event.target.value as "gptk" | "gpmc" | "gp_disguise")}>
                <option value="gptk">gptk</option>
                <option value="gpmc">gpmc</option>
                <option value="gp_disguise">gp_disguise</option>
              </select>
            </label>

            <label>
              Operation
              <select value={advancedOperation} onChange={(event) => setAdvancedOperation(event.target.value)}>
                {providerOperations.map((item) => (
                  <option key={item.operation} value={item.operation}>
                    {item.operation}
                  </option>
                ))}
              </select>
            </label>

            <textarea value={advancedParamsText} onChange={(event) => setAdvancedParamsText(event.target.value)} rows={6} />
            <button disabled={busy || !activeAccountId}>Preview advanced operation</button>
          </form>
        </section>
      )}

      {previewDialog && (
        <section className="modal">
          <div className="modal-card card">
            <h2>{previewDialog.title}</h2>
            <p>Matched: {previewDialog.matchCount}</p>
            {previewDialog.warnings.map((warning) => (
              <p key={warning} className="warn">
                {warning}
              </p>
            ))}
            <div className="sample-list">
              {previewDialog.sampleItems.slice(0, 10).map((item) => (
                <div key={item}>{item}</div>
              ))}
            </div>
            <div className="modal-actions">
              <button onClick={() => void commitPreview()} disabled={busy}>
                Confirm Commit
              </button>
              <button onClick={() => setPreviewDialog(null)} className="ghost" disabled={busy}>
                Cancel
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
