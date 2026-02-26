import { useCallback, useEffect, useMemo, useState } from "react";

import { getJson, postJson } from "../api";
import type { ExplorerAlbum, ExplorerItem, ExplorerItemsResponse, ExplorerSource, Job } from "../types";

export type ViewMode = "grid" | "list";

type SelectionGesture = {
  shiftKey: boolean;
  metaKey: boolean;
  ctrlKey: boolean;
};

function buildItemsPath(params: {
  accountId: string;
  source: string;
  albumId: string | null;
  search: string;
  favorite: boolean | null;
  archived: boolean | null;
  cursor: string | null;
  pageSize?: number;
}) {
  const query = new URLSearchParams();
  query.set("account_id", params.accountId);
  query.set("page_size", String(params.pageSize || 160));
  if (params.cursor) query.set("page_cursor", params.cursor);
  if (params.source !== "albums") query.set("source", params.source);
  if (params.albumId) query.set("album_id", params.albumId);
  if (params.search.trim()) query.set("search", params.search.trim());
  if (params.favorite !== null) query.set("favorite", String(params.favorite));
  if (params.archived !== null) query.set("archived", String(params.archived));
  return `/api/v2/explorer/items?${query.toString()}`;
}

export function useExplorer(accountId: string) {
  const [sources, setSources] = useState<ExplorerSource[]>([]);
  const [albums, setAlbums] = useState<ExplorerAlbum[]>([]);
  const [items, setItems] = useState<ExplorerItem[]>([]);

  const [activeSource, setActiveSource] = useState("library");
  const [activeAlbumId, setActiveAlbumId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [favoriteFilter, setFavoriteFilter] = useState<boolean | null>(null);
  const [archivedFilter, setArchivedFilter] = useState<boolean | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("grid");

  const [pageCursor, setPageCursor] = useState<string | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);

  const [loadingSources, setLoadingSources] = useState(false);
  const [loadingAlbums, setLoadingAlbums] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);

  const [selectedKeys, setSelectedKeys] = useState<Set<string>>(new Set());
  const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);

  const selectedCount = selectedKeys.size;

  const selectedItems = useMemo(
    () => items.filter((item) => selectedKeys.has(item.media_key)),
    [items, selectedKeys]
  );

  const selectedPrimaryItem = selectedItems[0] || null;

  const refreshSources = useCallback(async () => {
    setLoadingSources(true);
    try {
      const rows = await getJson<ExplorerSource[]>("/api/v2/explorer/sources");
      setSources(rows);
      return rows;
    } finally {
      setLoadingSources(false);
    }
  }, []);

  const refreshAlbums = useCallback(async () => {
    if (!accountId) {
      setAlbums([]);
      return [];
    }
    setLoadingAlbums(true);
    try {
      const rows = await getJson<ExplorerAlbum[]>(`/api/v2/explorer/albums?account_id=${accountId}`);
      setAlbums(rows);
      if (activeAlbumId && rows.every((item) => item.media_key !== activeAlbumId)) {
        setActiveAlbumId(null);
        setActiveSource("library");
      }
      return rows;
    } finally {
      setLoadingAlbums(false);
    }
  }, [accountId, activeAlbumId]);

  const refreshItems = useCallback(async (reset: boolean) => {
    if (!accountId) {
      setItems([]);
      return;
    }
    const cursor = reset ? null : nextCursor;
    if (!reset && !cursor) {
      return;
    }

    setLoadingItems(true);
    try {
      const path = buildItemsPath({
        accountId,
        source: activeSource,
        albumId: activeAlbumId,
        search: debouncedSearch,
        favorite: favoriteFilter,
        archived: archivedFilter,
        cursor,
      });
      const response = await getJson<ExplorerItemsResponse>(path);
      setItems((prev) => (reset ? response.items : [...prev, ...response.items]));
      setPageCursor(cursor);
      setNextCursor(response.next_cursor);
      if (reset) {
        setSelectedKeys(new Set());
        setLastSelectedIndex(null);
        setFocusedIndex(response.items.length ? 0 : null);
      }
    } finally {
      setLoadingItems(false);
    }
  }, [accountId, activeSource, activeAlbumId, debouncedSearch, favoriteFilter, archivedFilter, nextCursor]);

  const queueRefreshIndex = useCallback(async (maxItems: number = 5000) => {
    if (!accountId) {
      throw new Error("No account selected");
    }
    return await postJson<Job>("/api/v2/explorer/index/refresh", {
      account_id: accountId,
      max_items: maxItems,
      include_album_members: true,
      force_full: false,
    });
  }, [accountId]);

  const loadMore = useCallback(async () => {
    await refreshItems(false);
  }, [refreshItems]);

  const clearSelection = useCallback(() => {
    setSelectedKeys(new Set());
    setLastSelectedIndex(null);
  }, []);

  const toggleSelectAllLoaded = useCallback(() => {
    setSelectedKeys((prev) => {
      if (items.length > 0 && prev.size === items.length) {
        return new Set();
      }
      return new Set(items.map((item) => item.media_key));
    });
    setLastSelectedIndex(null);
  }, [items]);

  const selectByGesture = useCallback((mediaKey: string, index: number, gesture: SelectionGesture) => {
    setSelectedKeys((prev) => {
      const next = new Set(prev);
      const isMultiToggle = gesture.metaKey || gesture.ctrlKey;

      if (gesture.shiftKey && lastSelectedIndex !== null) {
        const start = Math.min(lastSelectedIndex, index);
        const end = Math.max(lastSelectedIndex, index);
        for (let i = start; i <= end; i += 1) {
          const key = items[i]?.media_key;
          if (key) next.add(key);
        }
        return next;
      }

      if (isMultiToggle) {
        if (next.has(mediaKey)) {
          next.delete(mediaKey);
        } else {
          next.add(mediaKey);
        }
        return next;
      }

      return new Set([mediaKey]);
    });

    setLastSelectedIndex(index);
    setFocusedIndex(index);
  }, [items, lastSelectedIndex]);

  const focusItem = useCallback((index: number | null) => {
    if (index === null || items.length === 0) {
      setFocusedIndex(null);
      return;
    }
    const clamped = Math.max(0, Math.min(index, items.length - 1));
    setFocusedIndex(clamped);
  }, [items]);

  const moveFocus = useCallback((delta: number, extendSelection: boolean = false) => {
    if (!items.length) return;
    const base = focusedIndex ?? (delta >= 0 ? 0 : items.length - 1);
    const next = Math.max(0, Math.min(base + delta, items.length - 1));
    setFocusedIndex(next);
    if (extendSelection) {
      const key = items[next]?.media_key;
      if (key) {
        selectByGesture(key, next, { shiftKey: true, metaKey: false, ctrlKey: false });
      }
    }
  }, [items, focusedIndex, selectByGesture]);

  const selectFocused = useCallback((mode: "replace" | "toggle" | "extend" = "replace") => {
    if (focusedIndex === null || focusedIndex < 0 || focusedIndex >= items.length) return;
    const mediaKey = items[focusedIndex]?.media_key;
    if (!mediaKey) return;
    if (mode === "toggle") {
      selectByGesture(mediaKey, focusedIndex, { shiftKey: false, metaKey: true, ctrlKey: true });
      return;
    }
    if (mode === "extend") {
      selectByGesture(mediaKey, focusedIndex, { shiftKey: true, metaKey: false, ctrlKey: false });
      return;
    }
    selectByGesture(mediaKey, focusedIndex, { shiftKey: false, metaKey: false, ctrlKey: false });
  }, [focusedIndex, items, selectByGesture]);

  const currentQueryForAction = useMemo(() => {
    return {
      source: activeSource !== "albums" ? activeSource : undefined,
      album_id: activeAlbumId || undefined,
      search: debouncedSearch.trim() || undefined,
      favorite: favoriteFilter ?? undefined,
      archived: archivedFilter ?? undefined,
      page_size: 500,
    };
  }, [activeSource, activeAlbumId, debouncedSearch, favoriteFilter, archivedFilter]);

  useEffect(() => {
    void refreshSources();
  }, [refreshSources]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(search);
    }, 180);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (!accountId) {
      setAlbums([]);
      setItems([]);
      setFocusedIndex(null);
      clearSelection();
      return;
    }
    void refreshAlbums();
  }, [accountId, refreshAlbums, clearSelection]);

  useEffect(() => {
    if (!accountId) {
      return;
    }
    void refreshItems(true);
  }, [accountId, activeSource, activeAlbumId, debouncedSearch, favoriteFilter, archivedFilter, refreshItems]);

  useEffect(() => {
    if (items.length === 0) {
      setFocusedIndex(null);
      return;
    }
    setFocusedIndex((prev) => {
      if (prev === null) return 0;
      return Math.max(0, Math.min(prev, items.length - 1));
    });
  }, [items]);

  return {
    sources,
    albums,
    items,
    selectedItems,
    selectedPrimaryItem,
    selectedKeys,
    selectedCount,
    focusedIndex,
    activeSource,
    setActiveSource,
    activeAlbumId,
    setActiveAlbumId,
    search,
    setSearch,
    favoriteFilter,
    setFavoriteFilter,
    archivedFilter,
    setArchivedFilter,
    viewMode,
    setViewMode,
    pageCursor,
    nextCursor,
    loadingSources,
    loadingAlbums,
    loadingItems,
    refreshSources,
    refreshAlbums,
    refreshItems,
    queueRefreshIndex,
    loadMore,
    clearSelection,
    toggleSelectAllLoaded,
    selectByGesture,
    focusItem,
    moveFocus,
    selectFocused,
    currentQueryForAction,
  };
}
