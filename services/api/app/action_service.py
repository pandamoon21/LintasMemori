from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .explorer_service import ExplorerService
from .job_store import create_job
from .models import Account, MediaIndex, PreviewAction
from .schemas import ActionPreviewRequest, ActionPreviewResult, ExplorerQuery


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActionService:
    def __init__(self, session: Session, account: Account) -> None:
        self.session = session
        self.account = account
        self.explorer = ExplorerService(session, account)

    def cleanup_expired(self) -> None:
        self.session.execute(delete(PreviewAction).where(PreviewAction.expires_at < utc_now()))
        self.session.commit()

    def create_preview(self, payload: ActionPreviewRequest) -> ActionPreviewResult:
        self.cleanup_expired()
        media_keys, warnings = self._resolve_target_keys(payload.query, payload.selected_media_keys)
        sample_rows = self._sample_rows(media_keys, limit=12)

        preview = PreviewAction(
            account_id=self.account.id,
            kind="explorer_action",
            action=payload.action,
            query_payload=(payload.query.model_dump() if payload.query else {}),
            action_params=payload.action_params,
            matched_media_keys=media_keys,
            sample_items=[self.explorer._to_item(item).model_dump(mode="json") for item in sample_rows],  # noqa: SLF001
            warnings=warnings,
            requires_confirm=True,
            status="previewed",
            expires_at=utc_now() + timedelta(minutes=settings.preview_ttl_minutes),
        )
        self.session.add(preview)
        self.session.commit()
        self.session.refresh(preview)

        return ActionPreviewResult(
            preview_id=preview.id,
            match_count=len(media_keys),
            sample_items=[self.explorer._to_item(item) for item in sample_rows],  # noqa: SLF001
            warnings=list(preview.warnings or []),
            requires_confirm=True,
        )

    def commit_preview(self, preview_id: str, confirm: bool) -> dict[str, Any]:
        preview = self.session.get(PreviewAction, preview_id)
        if preview is None or preview.account_id != self.account.id:
            raise RuntimeError("Preview not found")
        if preview.expires_at < utc_now():
            preview.status = "expired"
            self.session.commit()
            raise RuntimeError("Preview expired")
        if preview.status != "previewed":
            raise RuntimeError("Preview already committed or invalid")
        if preview.requires_confirm and not confirm:
            raise RuntimeError("Commit requires explicit confirm=true")

        provider, operation, params = self._build_job_params(preview)
        job = create_job(
            self.session,
            account_id=self.account.id,
            provider=provider,
            operation=operation,
            params=params,
            dry_run=False,
            message=f"Queued from preview {preview.id}",
        )

        preview.status = "committed"
        preview.committed_job_id = job.id
        preview.updated_at = utc_now()
        self.session.commit()

        return {"preview_id": preview.id, "job_id": job.id, "status": "queued"}

    def get_preview(self, preview_id: str) -> PreviewAction | None:
        preview = self.session.get(PreviewAction, preview_id)
        if preview is None or preview.account_id != self.account.id:
            return None
        return preview

    def _resolve_target_keys(self, query: ExplorerQuery | None, selected: list[str] | None) -> tuple[list[str], list[str]]:
        warnings: list[str] = []
        if selected:
            dedup = list(dict.fromkeys([str(item) for item in selected if item]))
            return dedup, warnings

        if query is None:
            return [], warnings

        collected: list[str] = []
        cursor = query.page_cursor
        max_collect = 5000
        while len(collected) < max_collect:
            q = query.model_copy(deep=True)
            q.page_size = min(q.page_size, 500)
            q.page_cursor = cursor
            result = self.explorer.query_items(q)
            if not result.items:
                break
            for item in result.items:
                collected.append(item.media_key)
                if len(collected) >= max_collect:
                    warnings.append("Result was truncated to 5000 items for safety")
                    break
            if len(collected) >= max_collect:
                break
            cursor = result.next_cursor
            if not cursor:
                break
        return list(dict.fromkeys(collected)), warnings

    def _sample_rows(self, media_keys: list[str], limit: int) -> list[MediaIndex]:
        if not media_keys:
            return []
        rows = self.session.execute(
            select(MediaIndex)
            .where(MediaIndex.account_id == self.account.id, MediaIndex.media_key.in_(media_keys[: max(limit * 8, 1)]))
            .limit(limit)
        ).scalars().all()
        return rows

    def _build_job_params(self, preview: PreviewAction) -> tuple[str, str, dict[str, Any]]:
        media_keys = [str(item) for item in (preview.matched_media_keys or []) if item]
        if not media_keys:
            raise RuntimeError("Preview has no matching media keys")

        rows = self.session.execute(
            select(MediaIndex).where(MediaIndex.account_id == self.account.id, MediaIndex.media_key.in_(media_keys))
        ).scalars().all()
        dedup_keys = [str(item.dedup_key) for item in rows if item.dedup_key]

        action = preview.action.strip().lower()
        action_params = dict(preview.action_params or {})

        if action in {"trash", "move_to_trash"}:
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for trash action")
            return "gptk", "gptk.move_items_to_trash", {"dedupKeyArray": dedup_keys, "confirmed": True}

        if action in {"restore", "restore_from_trash"}:
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for restore action")
            return "gptk", "gptk.restore_from_trash", {"dedupKeyArray": dedup_keys, "confirmed": True}

        if action == "archive":
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for archive action")
            return "gptk", "gptk.set_archive", {"dedupKeyArray": dedup_keys, "action": True, "confirmed": True}

        if action == "unarchive":
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for unarchive action")
            return "gptk", "gptk.set_archive", {"dedupKeyArray": dedup_keys, "action": False, "confirmed": True}

        if action == "favorite":
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for favorite action")
            return "gptk", "gptk.set_favorite", {"dedupKeyArray": dedup_keys, "action": True, "confirmed": True}

        if action == "unfavorite":
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for unfavorite action")
            return "gptk", "gptk.set_favorite", {"dedupKeyArray": dedup_keys, "action": False, "confirmed": True}

        if action == "add_album":
            album_media_key = action_params.get("album_id")
            album_name = action_params.get("album_name")
            if not album_media_key and not album_name:
                raise RuntimeError("add_album requires action_params.album_id or action_params.album_name")
            params: dict[str, Any] = {"mediaKeyArray": media_keys, "confirmed": True}
            if album_media_key:
                params["albumMediaKey"] = album_media_key
            if album_name:
                params["albumName"] = album_name
            return "gptk", "gptk.add_items_to_album", params

        if action == "remove_album":
            album_media_key = action_params.get("album_id")
            if not album_media_key:
                raise RuntimeError("remove_album requires action_params.album_id")
            return (
                "gptk",
                "gptk.remove_items_from_shared_album",
                {"albumMediaKey": album_media_key, "mediaKeyArray": media_keys, "confirmed": True},
            )

        if action in {"set_datetime", "set_timestamp"}:
            timestamp_sec = action_params.get("timestamp_sec")
            timezone_sec = int(action_params.get("timezone_sec", 0))
            if timestamp_sec is None:
                raise RuntimeError("set_datetime requires action_params.timestamp_sec")
            if not dedup_keys:
                raise RuntimeError("No dedup keys available for timestamp action")
            items = [{"dedupKey": key, "timestampSec": int(timestamp_sec), "timezoneSec": timezone_sec} for key in dedup_keys]
            return "gptk", "gptk.set_items_timestamp", {"items": items, "confirmed": True}

        raise RuntimeError(f"Unsupported action: {preview.action}")
