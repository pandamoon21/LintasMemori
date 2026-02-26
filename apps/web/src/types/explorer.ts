export type ExplorerSource = {
  id: string;
  label: string;
  icon: string;
};

export type ExplorerAlbum = {
  media_key: string;
  title: string | null;
  owner_actor_id: string | null;
  item_count: number | null;
  creation_timestamp: number | null;
  modified_timestamp: number | null;
  is_shared: boolean;
  thumb: string | null;
};

export type ExplorerItem = {
  media_key: string;
  dedup_key: string | null;
  timestamp_taken: number | null;
  timestamp_uploaded: number | null;
  file_name: string | null;
  size: number | null;
  type: string | null;
  is_archived: boolean;
  is_favorite: boolean;
  is_trashed: boolean;
  album_ids: string[];
  thumb_url: string | null;
  owner: string | null;
  space_flags: Record<string, unknown>;
  source: string;
};

export type ExplorerItemsResponse = {
  items: ExplorerItem[];
  next_cursor: string | null;
  total_returned: number;
};
