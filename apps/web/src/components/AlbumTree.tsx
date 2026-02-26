import type { ExplorerAlbum } from "../types";

type AlbumTreeProps = {
  albums: ExplorerAlbum[];
  activeAlbumId: string | null;
  onSelectAlbum: (albumId: string) => void;
  loading: boolean;
};

export function AlbumTree({ albums, activeAlbumId, onSelectAlbum, loading }: AlbumTreeProps) {
  if (loading) {
    return <div className="lm-muted">Loading albums...</div>;
  }

  if (!albums.length) {
    return <div className="lm-muted">No albums indexed yet.</div>;
  }

  return (
    <div className="lm-list-scroll">
      {albums.map((album) => (
        <button
          key={album.media_key}
          className={activeAlbumId === album.media_key ? "lm-list-item active" : "lm-list-item"}
          onClick={() => onSelectAlbum(album.media_key)}
          type="button"
        >
          <span className="lm-list-item-main">{album.title || album.media_key.slice(0, 8)}</span>
          <span className="lm-list-item-meta">{album.item_count ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
