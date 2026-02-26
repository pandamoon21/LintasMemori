from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Optional

from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.orm import Session

from .gptk_service import GptkService
from .models import Account, AlbumIndex, MediaIndex
from .schemas import ExplorerItem, ExplorerItemDetail, ExplorerItemsResponse, ExplorerQuery, ExplorerSourceOut

ProgressFn = Callable[[float, str], None]


EXPLORER_SOURCES = [
    ExplorerSourceOut(id="library", label="Library", icon="library"),
    ExplorerSourceOut(id="favorites", label="Favorites", icon="star"),
    ExplorerSourceOut(id="trash", label="Trash", icon="delete"),
    ExplorerSourceOut(id="locked_folder", label="Locked Folder", icon="lock"),
    ExplorerSourceOut(id="albums", label="Albums", icon="folder"),
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _encode_cursor(offset: int) -> str:
    return f"o:{max(offset, 0)}"


def _decode_cursor(cursor: Optional[str]) -> int:
    if not cursor:
        return 0
    if cursor.startswith("o:"):
        try:
            return max(int(cursor.split(":", 1)[1]), 0)
        except ValueError:
            return 0
    return 0


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for idx in range(0, len(values), size):
        yield values[idx : idx + size]


def _media_type_from_payload(file_name: Optional[str], duration: Any) -> Optional[str]:
    if duration:
        return "video"
    if not file_name:
        return None
    lower = file_name.lower()
    if lower.endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
        return "video"
    if lower.endswith((".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif")):
        return "image"
    return None


@dataclass
class _PageResult:
    items: list[dict[str, Any]]
    next_page_id: Optional[str]


class ExplorerService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account
        self.gptk = GptkService(session, account)

    def sources(self) -> list[ExplorerSourceOut]:
        return EXPLORER_SOURCES

    def list_albums(self) -> list[AlbumIndex]:
        rows = self.session.execute(
            select(AlbumIndex).where(AlbumIndex.account_id == self.account.id).order_by(AlbumIndex.modified_timestamp.desc())
        ).scalars().all()
        return rows

    def get_item(self, media_key: str) -> Optional[ExplorerItemDetail]:
        row = self.session.get(MediaIndex, {"account_id": self.account.id, "media_key": media_key})
        if row is None:
            return None
        return self._to_item_detail(row)

    def query_items(self, query: ExplorerQuery) -> ExplorerItemsResponse:
        offset = _decode_cursor(query.page_cursor)
        page_size = query.page_size

        stmt = select(MediaIndex).where(MediaIndex.account_id == self.account.id)

        if query.source == "library":
            stmt = stmt.where(MediaIndex.is_trashed.is_(False))
        elif query.source == "trash":
            stmt = stmt.where(MediaIndex.is_trashed.is_(True))
        elif query.source == "favorites":
            stmt = stmt.where(and_(MediaIndex.is_favorite.is_(True), MediaIndex.is_trashed.is_(False)))
        elif query.source == "locked_folder":
            stmt = stmt.where(MediaIndex.source == "locked_folder")

        if query.favorite is not None:
            stmt = stmt.where(MediaIndex.is_favorite.is_(query.favorite))
        if query.archived is not None:
            stmt = stmt.where(MediaIndex.is_archived.is_(query.archived))
        if query.trashed is not None:
            stmt = stmt.where(MediaIndex.is_trashed.is_(query.trashed))
        if query.media_type:
            stmt = stmt.where(MediaIndex.media_type == query.media_type)
        if query.date_from is not None:
            stmt = stmt.where(MediaIndex.timestamp_taken >= query.date_from)
        if query.date_to is not None:
            stmt = stmt.where(MediaIndex.timestamp_taken <= query.date_to)
        if query.search:
            search = f"%{query.search.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(MediaIndex.file_name).like(search),
                    func.lower(MediaIndex.media_key).like(search),
                    func.lower(MediaIndex.dedup_key).like(search),
                )
            )
        if query.album_id:
            stmt = stmt.where(text("EXISTS (SELECT 1 FROM json_each(media_index.album_ids) WHERE json_each.value = :album_id)")).params(
                album_id=query.album_id
            )

        if query.sort == "timestamp_asc":
            stmt = stmt.order_by(MediaIndex.timestamp_taken.asc(), MediaIndex.media_key.asc())
        elif query.sort == "uploaded_desc":
            stmt = stmt.order_by(MediaIndex.timestamp_uploaded.desc(), MediaIndex.media_key.desc())
        else:
            stmt = stmt.order_by(MediaIndex.timestamp_taken.desc(), MediaIndex.media_key.desc())

        rows = self.session.execute(stmt.offset(offset).limit(page_size + 1)).scalars().all()
        has_more = len(rows) > page_size
        visible = rows[:page_size]
        next_cursor = _encode_cursor(offset + page_size) if has_more else None

        return ExplorerItemsResponse(
            items=[self._to_item(row) for row in visible],
            next_cursor=next_cursor,
            total_returned=len(visible),
        )

    def refresh_index(
        self,
        *,
        max_items: int = 3000,
        include_album_members: bool = False,
        force_full: bool = False,
        progress: Optional[ProgressFn] = None,
    ) -> dict[str, Any]:
        progress = progress or (lambda _v, _m: None)
        progress(0.03, "Refreshing explorer index")

        if force_full:
            self.session.execute(delete(MediaIndex).where(MediaIndex.account_id == self.account.id))
            self.session.execute(delete(AlbumIndex).where(AlbumIndex.account_id == self.account.id))
            self.session.commit()

        library_items = self._collect_library_items(max_items=max_items, progress=progress)
        media_keys: list[str] = []
        for item in library_items:
            media_key = str(item.get("mediaKey") or "")
            if not media_key:
                continue
            media_keys.append(media_key)
            self._upsert_media(item=item, source="library", is_trashed=False)
        self.session.commit()

        progress(0.42, "Syncing favorites and trash flags")
        favorite_keys = set(self._collect_simple_keys("gptk.get_favorite_items", max_items=max_items))
        trash_keys = set(self._collect_simple_keys("gptk.get_trash_items", max_items=max_items))

        existing_rows = self.session.execute(select(MediaIndex).where(MediaIndex.account_id == self.account.id)).scalars().all()
        for row in existing_rows:
            row.is_favorite = row.media_key in favorite_keys
            row.is_trashed = row.media_key in trash_keys
            row.source = "trash" if row.is_trashed else "library"
            row.updated_at = utc_now()
        self.session.commit()

        progress(0.55, "Syncing albums")
        albums = self._collect_albums(max_items=1000)
        album_keys = set()
        for album in albums:
            media_key = str(album.get("mediaKey") or "")
            if not media_key:
                continue
            album_keys.add(media_key)
            row = self.session.get(AlbumIndex, {"account_id": self.account.id, "media_key": media_key})
            if row is None:
                row = AlbumIndex(account_id=self.account.id, media_key=media_key)
                self.session.add(row)
            row.title = album.get("title")
            row.owner_actor_id = album.get("ownerActorId")
            row.item_count = album.get("itemCount")
            row.creation_timestamp = album.get("creationTimestamp")
            row.modified_timestamp = album.get("modifiedTimestamp")
            row.is_shared = bool(album.get("isShared"))
            row.thumb = album.get("thumb")
            row.updated_at = utc_now()

        if album_keys:
            self.session.execute(
                delete(AlbumIndex).where(
                    and_(AlbumIndex.account_id == self.account.id, AlbumIndex.media_key.not_in(list(album_keys)))
                )
            )
        self.session.commit()

        progress(0.7, "Pulling metadata batch")
        for chunk in _chunks(media_keys, 120):
            try:
                info_rows = self.gptk.call("gptk.get_batch_media_info", {"mediaKeyArray": chunk}).data
            except Exception:
                info_rows = []
            if not isinstance(info_rows, list):
                continue
            for info in info_rows:
                media_key = str(info.get("mediaKey") or "")
                if not media_key:
                    continue
                row = self.session.get(MediaIndex, {"account_id": self.account.id, "media_key": media_key})
                if row is None:
                    continue
                row.file_name = info.get("fileName") or row.file_name
                row.size = info.get("size") if info.get("size") is not None else row.size
                row.timestamp_uploaded = info.get("creationTimestamp") or row.timestamp_uploaded
                row.timestamp_taken = info.get("timestamp") or row.timestamp_taken
                row.space_flags = {
                    "takes_up_space": info.get("takesUpSpace"),
                    "space_taken": info.get("spaceTaken"),
                    "original_quality": info.get("isOriginalQuality"),
                }
                row.media_type = _media_type_from_payload(row.file_name, row.raw_item.get("duration"))
                row.updated_at = utc_now()
            self.session.commit()

        if include_album_members:
            progress(0.82, "Indexing album members")
            self._sync_album_memberships(list(album_keys), max_items_per_album=3000)

        progress(1.0, "Explorer index refresh complete")
        return {
            "library_items": len(media_keys),
            "favorite_items": len(favorite_keys),
            "trash_items": len(trash_keys),
            "albums": len(album_keys),
            "account_id": self.account.id,
        }

    def _collect_library_items(self, max_items: int, progress: ProgressFn) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_id: Optional[str] = None
        while len(items) < max_items:
            response = self.gptk.call("gptk.get_items_by_uploaded_date", {"pageId": page_id}).data
            page = self._parse_page(response)
            if not page.items:
                break
            items.extend(page.items)
            progress(min(0.35, 0.04 + (len(items) / max(max_items, 1)) * 0.31), f"Fetched {len(items)} library items")
            page_id = page.next_page_id
            if not page_id:
                break
        return items[:max_items]

    def _collect_simple_keys(self, operation: str, max_items: int) -> list[str]:
        keys: list[str] = []
        page_id: Optional[str] = None
        while len(keys) < max_items:
            response = self.gptk.call(operation, {"pageId": page_id}).data
            page = self._parse_page(response)
            if not page.items:
                break
            for item in page.items:
                media_key = item.get("mediaKey")
                if media_key:
                    keys.append(str(media_key))
            page_id = page.next_page_id
            if not page_id:
                break
        return keys[:max_items]

    def _collect_albums(self, max_items: int) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_id: Optional[str] = None
        while len(items) < max_items:
            response = self.gptk.call("gptk.get_albums", {"pageId": page_id}).data
            page = self._parse_page(response)
            if not page.items:
                break
            items.extend(page.items)
            page_id = page.next_page_id
            if not page_id:
                break
        return items[:max_items]

    def _sync_album_memberships(self, album_keys: list[str], max_items_per_album: int) -> None:
        rows = self.session.execute(select(MediaIndex).where(MediaIndex.account_id == self.account.id)).scalars().all()
        for row in rows:
            row.album_ids = []
            row.updated_at = utc_now()
        self.session.commit()

        for album_key in album_keys:
            page_id: Optional[str] = None
            count = 0
            while count < max_items_per_album:
                response = self.gptk.call("gptk.get_album_page", {"albumMediaKey": album_key, "pageId": page_id}).data
                page = self._parse_page(response)
                if not page.items:
                    break
                for item in page.items:
                    media_key = str(item.get("mediaKey") or "")
                    if not media_key:
                        continue
                    row = self.session.get(MediaIndex, {"account_id": self.account.id, "media_key": media_key})
                    if row is None:
                        row = MediaIndex(account_id=self.account.id, media_key=media_key, source="library", raw_item=item)
                        self.session.add(row)
                    albums = list(row.album_ids or [])
                    if album_key not in albums:
                        albums.append(album_key)
                    row.album_ids = albums
                    row.updated_at = utc_now()
                    count += 1
                self.session.commit()
                page_id = page.next_page_id
                if not page_id:
                    break

    @staticmethod
    def _parse_page(payload: Any) -> _PageResult:
        if isinstance(payload, dict):
            items = payload.get("items")
            next_page_id = payload.get("nextPageId")
            return _PageResult(items=items if isinstance(items, list) else [], next_page_id=next_page_id)
        return _PageResult(items=[], next_page_id=None)

    def _upsert_media(self, item: dict[str, Any], source: str, is_trashed: bool) -> None:
        media_key = str(item.get("mediaKey") or "")
        if not media_key:
            return
        row = self.session.get(MediaIndex, {"account_id": self.account.id, "media_key": media_key})
        if row is None:
            row = MediaIndex(account_id=self.account.id, media_key=media_key)
            self.session.add(row)

        row.dedup_key = item.get("dedupKey") or row.dedup_key
        row.timestamp_taken = item.get("timestamp") or row.timestamp_taken
        row.timestamp_uploaded = item.get("creationTimestamp") or row.timestamp_uploaded
        row.timezone_offset = item.get("timezoneOffset") or row.timezone_offset
        row.thumb_url = item.get("thumb") or row.thumb_url
        row.is_archived = bool(item.get("isArchived") or False)
        row.is_favorite = bool(item.get("isFavorite") or row.is_favorite)
        row.is_trashed = is_trashed
        row.source = source
        row.media_type = _media_type_from_payload(row.file_name, item.get("duration"))
        row.raw_item = item
        row.updated_at = utc_now()

    @staticmethod
    def _to_item(row: MediaIndex) -> ExplorerItem:
        return ExplorerItem(
            media_key=row.media_key,
            dedup_key=row.dedup_key,
            timestamp_taken=row.timestamp_taken,
            timestamp_uploaded=row.timestamp_uploaded,
            file_name=row.file_name,
            size=row.size,
            type=row.media_type,
            is_archived=row.is_archived,
            is_favorite=row.is_favorite,
            is_trashed=row.is_trashed,
            album_ids=list(row.album_ids or []),
            thumb_url=row.thumb_url,
            owner=row.owner_name,
            space_flags=dict(row.space_flags or {}),
            source=row.source,
        )

    def _to_item_detail(self, row: MediaIndex) -> ExplorerItemDetail:
        payload = self._to_item(row).model_dump()
        payload["raw_item"] = dict(row.raw_item or {})
        return ExplorerItemDetail(**payload)
