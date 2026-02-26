import { useCallback, useEffect, useMemo, useState } from "react";

import { getJson } from "./api";
import { AppShell } from "./components/AppShell";
import { AdvancedDrawer } from "./components/AdvancedDrawer";
import { ExplorerToolbar } from "./components/ExplorerToolbar";
import { MediaView } from "./components/MediaView";
import { PipelineWizardDrawer } from "./components/PipelineWizardDrawer";
import { PreviewConfirmModal } from "./components/PreviewConfirmModal";
import { SelectionActionBar } from "./components/SelectionActionBar";
import { SetupDrawer } from "./components/SetupDrawer";
import { SourceSidebar } from "./components/SourceSidebar";
import { TaskCenter } from "./components/TaskCenter";
import { TopBar } from "./components/TopBar";
import { UploadWizardDrawer } from "./components/UploadWizardDrawer";
import { useAccounts } from "./hooks/useAccounts";
import { useActionPreviewCommit } from "./hooks/useActionPreviewCommit";
import { useDrawers } from "./hooks/useDrawers";
import { useExplorer } from "./hooks/useExplorer";
import { useJobsStream } from "./hooks/useJobsStream";
import type { OperationCatalogEntry } from "./types";

const DEFAULT_ACTION_DATE = new Date().toISOString().slice(0, 16);

function isTextInputElement(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  const tag = target.tagName.toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return true;
  if (target.getAttribute("contenteditable") === "true") return true;
  return false;
}

export function App() {
  const accounts = useAccounts();
  const explorer = useExplorer(accounts.activeAccountId);
  const jobs = useJobsStream(accounts.activeAccountId);
  const drawers = useDrawers("setup");

  const [operations, setOperations] = useState<OperationCatalogEntry[]>([]);
  const [selectedDateTime, setSelectedDateTime] = useState(DEFAULT_ACTION_DATE);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const resetNotice = useCallback(() => {
    setError(null);
    setMessage(null);
  }, []);

  const runSafe = useCallback(async (fn: () => Promise<void>, successMessage?: string) => {
    resetNotice();
    try {
      await fn();
      if (successMessage) {
        setMessage(successMessage);
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }, [resetNotice]);

  const handleCommittedPreview = useCallback(async () => {
    await Promise.all([jobs.refreshJobs(), explorer.refreshItems(true)]);
    explorer.clearSelection();
    setMessage("Commit queued as async job.");
  }, [jobs, explorer]);

  const previewFlow = useActionPreviewCommit(handleCommittedPreview);

  const loadOperations = useCallback(async () => {
    const rows = await getJson<OperationCatalogEntry[]>("/api/v2/advanced/operations");
    setOperations(rows);
  }, []);

  const bootstrap = useCallback(async () => {
    await Promise.all([accounts.refreshAccounts(), jobs.refreshJobs(), loadOperations()]);
  }, [accounts, jobs, loadOperations]);

  useEffect(() => {
    void runSafe(async () => {
      await bootstrap();
    });
  }, [bootstrap, runSafe]);

  const busy =
    accounts.loading ||
    previewFlow.loading ||
    jobs.loading;

  const noAccount = !accounts.activeAccountId;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (isTextInputElement(event.target)) return;

      const lowerKey = event.key.toLowerCase();
      const useMeta = event.metaKey || event.ctrlKey;

      if (useMeta && lowerKey === "a") {
        event.preventDefault();
        explorer.toggleSelectAllLoaded();
        return;
      }

      if (event.key === "Escape") {
        if (previewFlow.preview) {
          event.preventDefault();
          previewFlow.closePreview();
          return;
        }
        if (explorer.selectedCount > 0) {
          event.preventDefault();
          explorer.clearSelection();
          return;
        }
      }

      if (noAccount || explorer.items.length === 0) return;

      const verticalStep = explorer.viewMode === "grid" ? 4 : 1;
      if (event.key === "ArrowRight") {
        event.preventDefault();
        explorer.moveFocus(1, event.shiftKey);
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        explorer.moveFocus(-1, event.shiftKey);
        return;
      }
      if (event.key === "ArrowDown") {
        event.preventDefault();
        explorer.moveFocus(verticalStep, event.shiftKey);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        explorer.moveFocus(-verticalStep, event.shiftKey);
        return;
      }
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (useMeta) {
          explorer.selectFocused("toggle");
          return;
        }
        if (event.shiftKey) {
          explorer.selectFocused("extend");
          return;
        }
        explorer.selectFocused("replace");
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    explorer.toggleSelectAllLoaded,
    explorer.selectedCount,
    explorer.clearSelection,
    explorer.items.length,
    explorer.viewMode,
    explorer.moveFocus,
    explorer.selectFocused,
    previewFlow.preview,
    previewFlow.closePreview,
    noAccount,
  ]);

  const handleRefreshIndex = useCallback(() => {
    void runSafe(async () => {
      await explorer.queueRefreshIndex();
      await jobs.refreshJobs();
    }, "Explorer index refresh queued.");
  }, [runSafe, explorer, jobs]);

  const handleSelectSource = useCallback((sourceId: string) => {
    explorer.setActiveSource(sourceId);
    explorer.setActiveAlbumId(null);
  }, [explorer]);

  const handleSelectAlbum = useCallback((albumId: string) => {
    explorer.setActiveSource("albums");
    explorer.setActiveAlbumId(albumId);
  }, [explorer]);

  const buildActionPayload = useCallback(
    (action: string, actionParams: Record<string, unknown>) => {
      if (!accounts.activeAccountId) {
        throw new Error("No account selected");
      }

      if (explorer.selectedCount > 0) {
        return {
          account_id: accounts.activeAccountId,
          selected_media_keys: Array.from(explorer.selectedKeys),
          action,
          action_params: actionParams,
        };
      }

      return {
        account_id: accounts.activeAccountId,
        query: explorer.currentQueryForAction,
        action,
        action_params: actionParams,
      };
    },
    [accounts.activeAccountId, explorer]
  );

  const openCoreActionPreview = useCallback(
    async (action: string, actionParams: Record<string, unknown> = {}) => {
      const payload = buildActionPayload(action, actionParams);
      await previewFlow.previewAction(payload, `Preview action: ${action}`);
    },
    [buildActionPayload, previewFlow]
  );

  const onTrash = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("trash");
    });
  }, [runSafe, openCoreActionPreview]);

  const onRestore = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("restore");
    });
  }, [runSafe, openCoreActionPreview]);

  const onArchive = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("archive");
    });
  }, [runSafe, openCoreActionPreview]);

  const onUnarchive = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("unarchive");
    });
  }, [runSafe, openCoreActionPreview]);

  const onFavorite = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("favorite");
    });
  }, [runSafe, openCoreActionPreview]);

  const onUnfavorite = useCallback(() => {
    void runSafe(async () => {
      await openCoreActionPreview("unfavorite");
    });
  }, [runSafe, openCoreActionPreview]);

  const onAddAlbum = useCallback(() => {
    void runSafe(async () => {
      const raw = window.prompt("Masukkan album_id atau ketik name:NamaAlbum");
      if (!raw) return;
      if (raw.startsWith("name:")) {
        await openCoreActionPreview("add_album", { album_name: raw.slice(5).trim() });
        return;
      }
      await openCoreActionPreview("add_album", { album_id: raw.trim() });
    });
  }, [runSafe, openCoreActionPreview]);

  const onRemoveAlbum = useCallback(() => {
    void runSafe(async () => {
      const albumId = explorer.activeAlbumId || window.prompt("Masukkan album_id untuk remove") || "";
      if (!albumId.trim()) return;
      await openCoreActionPreview("remove_album", { album_id: albumId.trim() });
    });
  }, [runSafe, openCoreActionPreview, explorer.activeAlbumId]);

  const onSetDate = useCallback(() => {
    void runSafe(async () => {
      const date = new Date(selectedDateTime);
      if (Number.isNaN(date.getTime())) {
        throw new Error("Invalid date/time format");
      }
      const timezoneSec = -date.getTimezoneOffset() * 60;
      await openCoreActionPreview("set_datetime", {
        timestamp_sec: Math.floor(date.getTime() / 1000),
        timezone_sec: timezoneSec,
      });
    });
  }, [runSafe, selectedDateTime, openCoreActionPreview]);

  const handlePreviewUpload = useCallback(
    async (payload: { target: string; recursive: boolean; albumName: string }) => {
      if (!accounts.activeAccountId) {
        throw new Error("No account selected");
      }
      await previewFlow.previewUpload({
        account_id: accounts.activeAccountId,
        target: payload.target,
        recursive: payload.recursive,
        gpmc_upload_options: {
          album_name: payload.albumName.trim() || undefined,
        },
      });
    },
    [accounts.activeAccountId, previewFlow]
  );

  const handlePreviewPipeline = useCallback(
    async (payload: {
      inputLines: string;
      disguiseType: "image" | "video";
      separator: string;
      outputDir: string;
      keepArtifacts: boolean;
      albumName: string;
    }) => {
      if (!accounts.activeAccountId) {
        throw new Error("No account selected");
      }

      const inputFiles = payload.inputLines
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);

      if (!inputFiles.length) {
        throw new Error("No input files or patterns specified");
      }

      await previewFlow.previewPipeline({
        account_id: accounts.activeAccountId,
        input_files: inputFiles,
        disguise_type: payload.disguiseType,
        separator: payload.separator,
        output_policy: {
          keep_artifacts: payload.keepArtifacts,
          output_dir: payload.outputDir.trim() || undefined,
        },
        gpmc_upload_options: {
          album_name: payload.albumName.trim() || undefined,
        },
      });
    },
    [accounts.activeAccountId, previewFlow]
  );

  const handlePreviewAdvanced = useCallback(
    async (payload: {
      provider: "gptk" | "gpmc" | "gp_disguise";
      operation: string;
      params: Record<string, unknown>;
    }) => {
      if (!accounts.activeAccountId) {
        throw new Error("No account selected");
      }
      await previewFlow.previewAdvanced({
        account_id: accounts.activeAccountId,
        provider: payload.provider,
        operation: payload.operation,
        params: payload.params,
      });
    },
    [accounts.activeAccountId, previewFlow]
  );

  const notices = useMemo(
    () => (
      <>
        {error ? (
          <div className="lm-notice error">
            <span>{error}</span>
            <button className="lm-btn-ghost" onClick={() => void runSafe(async () => await bootstrap())}>
              Retry bootstrap
            </button>
          </div>
        ) : null}
        {message ? <div className="lm-notice info">{message}</div> : null}
      </>
    ),
    [error, message, runSafe, bootstrap]
  );

  return (
    <AppShell
      topBar={
        <TopBar
          accounts={accounts.accounts}
          activeAccountId={accounts.activeAccountId}
          onAccountChange={accounts.setActiveAccountId}
          onRefreshIndex={handleRefreshIndex}
          onToggleDrawer={drawers.toggleDrawer}
          busy={busy}
          activeJobs={jobs.activeCount}
        />
      }
      notices={notices}
      sidebar={
        <SourceSidebar
          sources={explorer.sources}
          albums={explorer.albums}
          activeSource={explorer.activeSource}
          activeAlbumId={explorer.activeAlbumId}
          onSelectSource={handleSelectSource}
          onSelectAlbum={handleSelectAlbum}
          loadingSources={explorer.loadingSources}
          loadingAlbums={explorer.loadingAlbums}
        />
      }
      explorer={
        <main className="lm-explorer">
          <ExplorerToolbar
            search={explorer.search}
            onSearchChange={explorer.setSearch}
            favoriteFilter={explorer.favoriteFilter}
            archivedFilter={explorer.archivedFilter}
            onToggleFavorite={() => explorer.setFavoriteFilter(explorer.favoriteFilter ? null : true)}
            onToggleArchived={() => explorer.setArchivedFilter(explorer.archivedFilter ? null : true)}
            viewMode={explorer.viewMode}
            onViewModeChange={explorer.setViewMode}
            onRefresh={() => void explorer.refreshItems(true)}
            loading={explorer.loadingItems}
          />

          <SelectionActionBar
            selectedCount={explorer.selectedCount}
            loadedCount={explorer.items.length}
            selectedDateTime={selectedDateTime}
            onDateTimeChange={setSelectedDateTime}
            onSelectAll={explorer.toggleSelectAllLoaded}
            onClearSelection={explorer.clearSelection}
            onTrash={onTrash}
            onRestore={onRestore}
            onArchive={onArchive}
            onUnarchive={onUnarchive}
            onFavorite={onFavorite}
            onUnfavorite={onUnfavorite}
            onAddAlbum={onAddAlbum}
            onRemoveAlbum={onRemoveAlbum}
            onSetDate={onSetDate}
            disabled={busy || noAccount}
          />

          <MediaView
            items={explorer.items}
            viewMode={explorer.viewMode}
            selectedKeys={explorer.selectedKeys}
            focusedIndex={explorer.focusedIndex}
            selectedPrimaryItem={explorer.selectedPrimaryItem}
            loading={explorer.loadingItems}
            onSelectItem={explorer.selectByGesture}
            onFocusItem={explorer.focusItem}
            nextCursor={explorer.nextCursor}
            onLoadMore={() => void explorer.loadMore()}
            busy={busy}
            pageCursor={explorer.pageCursor}
          />
        </main>
      }
      taskCenter={<TaskCenter jobs={jobs.jobs} activeCount={jobs.activeCount} onCancel={(jobId) => void runSafe(async () => await jobs.cancelJob(jobId))} busy={busy} />}
      drawers={
        <>
          <SetupDrawer
            open={drawers.openDrawer === "setup"}
            onClose={drawers.closeDrawer}
            accountLabel={accounts.activeAccount?.label || ""}
            busy={busy}
            hasAccount={!noAccount}
            onCreateAccount={async (label, emailHint) => {
              await runSafe(async () => {
                await accounts.createAccount(label, emailHint);
              }, "Account created.");
            }}
            onSaveGpmcAuth={async (authData) => {
              await runSafe(async () => {
                await accounts.saveGpmcAuth(authData);
              }, "gpmc credentials saved.");
            }}
            onPasteCookies={async (cookieText) => {
              await runSafe(async () => {
                await accounts.pasteCookies(cookieText);
              }, "Cookie string imported.");
            }}
            onImportCookieFile={async (file) => {
              await runSafe(async () => {
                await accounts.importCookieFile(file);
              }, "Cookie file imported.");
            }}
            onRefreshSession={async () => {
              await runSafe(async () => {
                await accounts.refreshSession();
              }, "Session refreshed.");
            }}
          />

          <UploadWizardDrawer
            open={drawers.openDrawer === "upload"}
            onClose={drawers.closeDrawer}
            busy={busy || noAccount}
            onPreviewUpload={async (payload) => {
              await runSafe(async () => {
                await handlePreviewUpload(payload);
              });
            }}
          />

          <PipelineWizardDrawer
            open={drawers.openDrawer === "pipeline"}
            onClose={drawers.closeDrawer}
            busy={busy || noAccount}
            onPreviewPipeline={async (payload) => {
              await runSafe(async () => {
                await handlePreviewPipeline(payload);
              });
            }}
          />

          <AdvancedDrawer
            open={drawers.openDrawer === "advanced"}
            onClose={drawers.closeDrawer}
            busy={busy || noAccount}
            operations={operations}
            onPreviewAdvanced={async (payload) => {
              await runSafe(async () => {
                await handlePreviewAdvanced(payload);
              });
            }}
          />
        </>
      }
      modal={
        <PreviewConfirmModal
          preview={previewFlow.preview}
          busy={previewFlow.loading}
          onConfirm={() =>
            void runSafe(async () => {
              await previewFlow.commitPreview();
            })
          }
          onClose={previewFlow.closePreview}
        />
      }
    />
  );
}
