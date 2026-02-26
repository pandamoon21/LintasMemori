import { AlbumTree } from "./AlbumTree";
import type { ExplorerAlbum, ExplorerSource } from "../types";

type SourceSidebarProps = {
  sources: ExplorerSource[];
  albums: ExplorerAlbum[];
  activeSource: string;
  activeAlbumId: string | null;
  onSelectSource: (sourceId: string) => void;
  onSelectAlbum: (albumId: string) => void;
  loadingSources: boolean;
  loadingAlbums: boolean;
};

export function SourceSidebar({
  sources,
  albums,
  activeSource,
  activeAlbumId,
  onSelectSource,
  onSelectAlbum,
  loadingSources,
  loadingAlbums,
}: SourceSidebarProps) {
  return (
    <aside className="lm-sidebar">
      <section className="lm-surface lm-panel">
        <h2>Sources</h2>
        {loadingSources ? <div className="lm-muted">Loading sources...</div> : null}
        <div className="lm-list-stack">
          {sources.map((source) => (
            <button
              key={source.id}
              className={activeSource === source.id && !activeAlbumId ? "lm-list-item active" : "lm-list-item"}
              onClick={() => onSelectSource(source.id)}
              type="button"
            >
              <span className="lm-list-item-main">{source.label}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="lm-surface lm-panel">
        <h2>Albums</h2>
        <AlbumTree
          albums={albums}
          activeAlbumId={activeAlbumId}
          onSelectAlbum={onSelectAlbum}
          loading={loadingAlbums}
        />
      </section>
    </aside>
  );
}
