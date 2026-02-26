from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..explorer_service import EXPLORER_SOURCES, ExplorerService
from ..job_store import create_job
from ..models import Account
from ..schemas import (
    ExplorerAlbumOut,
    ExplorerIndexRefreshRequest,
    ExplorerItemDetail,
    ExplorerItemsResponse,
    ExplorerQuery,
    ExplorerSourceOut,
    JobOut,
)
from ..serializers import job_to_out
from ..database import get_session

router = APIRouter(prefix="/api/v2/explorer", tags=["v2-explorer"])


def _require_account(session: Session, account_id: str) -> Account:
    account = session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get("/sources", response_model=list[ExplorerSourceOut])
def get_sources() -> list[ExplorerSourceOut]:
    return EXPLORER_SOURCES


@router.get("/albums", response_model=list[ExplorerAlbumOut])
def get_albums(account_id: str = Query(...), session: Session = Depends(get_session)) -> list[ExplorerAlbumOut]:
    account = _require_account(session, account_id)
    service = ExplorerService(session, account)
    rows = service.list_albums()
    return [
        ExplorerAlbumOut(
            media_key=item.media_key,
            title=item.title,
            owner_actor_id=item.owner_actor_id,
            item_count=item.item_count,
            creation_timestamp=item.creation_timestamp,
            modified_timestamp=item.modified_timestamp,
            is_shared=item.is_shared,
            thumb=item.thumb,
        )
        for item in rows
    ]


@router.get("/items", response_model=ExplorerItemsResponse)
def get_items(
    account_id: str = Query(...),
    source: str | None = Query(default=None),
    album_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    date_from: int | None = Query(default=None),
    date_to: int | None = Query(default=None),
    media_type: str | None = Query(default=None),
    favorite: bool | None = Query(default=None),
    archived: bool | None = Query(default=None),
    trashed: bool | None = Query(default=None),
    sort: str = Query(default="timestamp_desc"),
    page_cursor: str | None = Query(default=None),
    page_size: int = Query(default=120, ge=1, le=500),
    session: Session = Depends(get_session),
) -> ExplorerItemsResponse:
    account = _require_account(session, account_id)
    service = ExplorerService(session, account)
    query = ExplorerQuery(
        source=source,
        album_id=album_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        media_type=media_type,
        favorite=favorite,
        archived=archived,
        trashed=trashed,
        sort=sort,
        page_cursor=page_cursor,
        page_size=page_size,
    )
    return service.query_items(query)


@router.get("/items/{media_key}", response_model=ExplorerItemDetail)
def get_item(media_key: str, account_id: str = Query(...), session: Session = Depends(get_session)) -> ExplorerItemDetail:
    account = _require_account(session, account_id)
    service = ExplorerService(session, account)
    item = service.get_item(media_key)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found in index")
    return item


@router.post("/index/refresh", response_model=JobOut)
def refresh_index(payload: ExplorerIndexRefreshRequest, session: Session = Depends(get_session)) -> JobOut:
    _require_account(session, payload.account_id)
    job = create_job(
        session,
        account_id=payload.account_id,
        provider="indexer",
        operation="explorer.index.refresh",
        params={
            "max_items": payload.max_items,
            "include_album_members": payload.include_album_members,
            "force_full": payload.force_full,
            "confirmed": True,
        },
        dry_run=False,
        message="Queued explorer index refresh",
    )
    return job_to_out(job)
