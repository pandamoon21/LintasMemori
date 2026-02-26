import type { ViewMode } from "../hooks/useExplorer";

type ExplorerToolbarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  favoriteFilter: boolean | null;
  archivedFilter: boolean | null;
  onToggleFavorite: () => void;
  onToggleArchived: () => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onRefresh: () => void;
  loading: boolean;
};

export function ExplorerToolbar({
  search,
  onSearchChange,
  favoriteFilter,
  archivedFilter,
  onToggleFavorite,
  onToggleArchived,
  viewMode,
  onViewModeChange,
  onRefresh,
  loading,
}: ExplorerToolbarProps) {
  return (
    <section className="lm-surface lm-toolbar">
      <div className="lm-toolbar-row">
        <input
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search by filename, media key, dedup key"
          className="lm-search-input"
        />

        <button className={favoriteFilter ? "lm-btn-ghost active" : "lm-btn-ghost"} onClick={onToggleFavorite} type="button">
          Favorite
        </button>
        <button className={archivedFilter ? "lm-btn-ghost active" : "lm-btn-ghost"} onClick={onToggleArchived} type="button">
          Archived
        </button>
        <button onClick={onRefresh} disabled={loading} type="button">
          Refresh
        </button>
      </div>

      <div className="lm-toolbar-row compact">
        <span className="lm-muted">View</span>
        <button className={viewMode === "grid" ? "lm-btn-ghost active" : "lm-btn-ghost"} onClick={() => onViewModeChange("grid")} type="button">
          Grid
        </button>
        <button className={viewMode === "list" ? "lm-btn-ghost active" : "lm-btn-ghost"} onClick={() => onViewModeChange("list")} type="button">
          List
        </button>
      </div>
    </section>
  );
}
