import type { ExplorerItem } from "../types";
import type { ViewMode } from "../hooks/useExplorer";

type MediaViewProps = {
  items: ExplorerItem[];
  viewMode: ViewMode;
  selectedKeys: Set<string>;
  focusedIndex: number | null;
  selectedPrimaryItem: ExplorerItem | null;
  loading: boolean;
  onSelectItem: (
    mediaKey: string,
    index: number,
    gesture: { shiftKey: boolean; metaKey: boolean; ctrlKey: boolean }
  ) => void;
  onFocusItem: (index: number) => void;
  nextCursor: string | null;
  onLoadMore: () => void;
  busy: boolean;
  pageCursor: string | null;
};

function formatTimestamp(timestamp: number | null): string {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
}

function formatSize(size: number | null): string {
  if (!size || size <= 0) return "-";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function MediaGrid({
  items,
  selectedKeys,
  focusedIndex,
  onSelectItem,
  onFocusItem,
}: {
  items: ExplorerItem[];
  selectedKeys: Set<string>;
  focusedIndex: number | null;
  onSelectItem: MediaViewProps["onSelectItem"];
  onFocusItem: MediaViewProps["onFocusItem"];
}) {
  return (
    <div className="lm-media-grid">
      {items.map((item, index) => (
        <article
          key={item.media_key}
          className={`${selectedKeys.has(item.media_key) ? "lm-media-card selected" : "lm-media-card"} ${
            focusedIndex === index ? "focused" : ""
          }`}
          onClick={(event) =>
            onSelectItem(item.media_key, index, {
              shiftKey: event.shiftKey,
              metaKey: event.metaKey,
              ctrlKey: event.ctrlKey,
            })
          }
          onFocus={() => onFocusItem(index)}
          tabIndex={0}
        >
          <div className="lm-thumb">
            {item.thumb_url ? <img src={item.thumb_url} alt={item.file_name || item.media_key} loading="lazy" /> : <span>No preview</span>}
          </div>
          <div className="lm-media-meta">
            <h3>{item.file_name || item.media_key}</h3>
            <p>{formatTimestamp(item.timestamp_taken)}</p>
            <p>{item.type || "-"} · {formatSize(item.size)}</p>
            <div className="lm-badge-row">
              {item.is_trashed ? <span className="lm-badge warn">Trash</span> : null}
              {item.is_archived ? <span className="lm-badge">Archived</span> : null}
              {item.is_favorite ? <span className="lm-badge info">Favorite</span> : null}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function MediaList({
  items,
  selectedKeys,
  focusedIndex,
  onSelectItem,
  onFocusItem,
}: {
  items: ExplorerItem[];
  selectedKeys: Set<string>;
  focusedIndex: number | null;
  onSelectItem: MediaViewProps["onSelectItem"];
  onFocusItem: MediaViewProps["onFocusItem"];
}) {
  return (
    <div className="lm-media-list">
      {items.map((item, index) => (
        <button
          key={item.media_key}
          className={`${selectedKeys.has(item.media_key) ? "lm-list-row selected" : "lm-list-row"} ${
            focusedIndex === index ? "focused" : ""
          }`}
          onClick={(event) =>
            onSelectItem(item.media_key, index, {
              shiftKey: event.shiftKey,
              metaKey: event.metaKey,
              ctrlKey: event.ctrlKey,
            })
          }
          onFocus={() => onFocusItem(index)}
          type="button"
        >
          <span>{item.file_name || item.media_key}</span>
          <span>{formatTimestamp(item.timestamp_taken)}</span>
          <span>{item.type || "-"}</span>
          <span>{formatSize(item.size)}</span>
        </button>
      ))}
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="lm-media-grid">
      {Array.from({ length: 8 }).map((_, idx) => (
        <div key={idx} className="lm-media-card skeleton" />
      ))}
    </div>
  );
}

function DetailPanel({ item }: { item: ExplorerItem | null }) {
  if (!item) {
    return (
      <section className="lm-surface lm-detail-panel">
        <h3>Detail</h3>
        <p className="lm-muted">Select one item to inspect metadata.</p>
      </section>
    );
  }

  return (
    <section className="lm-surface lm-detail-panel">
      <h3>Detail</h3>
      <div className="lm-kv"><span>Name</span><span>{item.file_name || "-"}</span></div>
      <div className="lm-kv"><span>Media key</span><span className="lm-mono">{item.media_key}</span></div>
      <div className="lm-kv"><span>Taken</span><span>{formatTimestamp(item.timestamp_taken)}</span></div>
      <div className="lm-kv"><span>Uploaded</span><span>{formatTimestamp(item.timestamp_uploaded)}</span></div>
      <div className="lm-kv"><span>Type</span><span>{item.type || "-"}</span></div>
      <div className="lm-kv"><span>Size</span><span>{formatSize(item.size)}</span></div>
      <div className="lm-kv"><span>Albums</span><span>{item.album_ids.length}</span></div>
      <div className="lm-kv"><span>Flags</span><span>{item.is_trashed ? "trash " : ""}{item.is_archived ? "archived " : ""}{item.is_favorite ? "favorite" : "-"}</span></div>
    </section>
  );
}

export function MediaView({
  items,
  viewMode,
  selectedKeys,
  focusedIndex,
  selectedPrimaryItem,
  loading,
  onSelectItem,
  onFocusItem,
  nextCursor,
  onLoadMore,
  busy,
  pageCursor,
}: MediaViewProps) {
  return (
    <section className="lm-content-stack">
      <section className="lm-surface lm-media-surface">
        {loading && items.length === 0 ? <SkeletonGrid /> : null}

        {!loading && items.length === 0 ? <div className="lm-empty">No items found in this query.</div> : null}

        {items.length > 0 && viewMode === "grid" ? (
          <MediaGrid items={items} selectedKeys={selectedKeys} focusedIndex={focusedIndex} onSelectItem={onSelectItem} onFocusItem={onFocusItem} />
        ) : null}

        {items.length > 0 && viewMode === "list" ? (
          <MediaList items={items} selectedKeys={selectedKeys} focusedIndex={focusedIndex} onSelectItem={onSelectItem} onFocusItem={onFocusItem} />
        ) : null}

        <div className="lm-pagination-row">
          <button onClick={onLoadMore} disabled={!nextCursor || busy || loading} type="button">
            Load More
          </button>
          <span className="lm-muted">cursor: {pageCursor || "-"}</span>
        </div>
      </section>

      <DetailPanel item={selectedPrimaryItem} />
    </section>
  );
}
