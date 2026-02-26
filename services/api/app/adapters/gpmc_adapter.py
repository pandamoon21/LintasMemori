from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

from .common import AdapterResult, ProgressFn


def _collect_media_files(target: str | list[str], recursive: bool = False) -> list[Path]:
    targets = [target] if isinstance(target, str) else target
    files: list[Path] = []
    for raw in targets:
        path = Path(raw)
        if path.is_file():
            files.append(path)
            continue
        if not path.is_dir():
            continue
        if recursive:
            files.extend([p for p in path.rglob("*") if p.is_file()])
        else:
            files.extend([p for p in path.iterdir() if p.is_file()])

    media_files: list[Path] = []
    for file in files:
        mime, _ = mimetypes.guess_type(file.as_posix())
        if mime and (mime.startswith("image/") or mime.startswith("video/")):
            media_files.append(file)
    return media_files


def run(operation: str, params: dict[str, Any], auth_data: str | None, dry_run: bool, progress: ProgressFn) -> AdapterResult:
    op = operation.replace("gpmc.", "")

    if op == "upload":
        target = params.get("target")
        if not target:
            raise ValueError("gpmc.upload requires params.target")

        recursive = bool(params.get("recursive", False))
        media_files = _collect_media_files(target, recursive=recursive)

        if dry_run:
            return {
                "operation": "upload",
                "target_count": len(media_files),
                "sample": [p.as_posix() for p in media_files[:10]],
            }

        if not auth_data:
            raise RuntimeError("gpmc auth_data is missing for this account")

        progress(0.15, "Importing gpmc client")
        try:
            from gpmc import Client  # type: ignore
        except Exception as exc:
            raise RuntimeError("gpmc is not installed. Install package before running gpmc jobs.") from exc

        progress(0.3, "Starting upload")
        client = Client(auth_data=auth_data)
        result = client.upload(
            target=target,
            album_name=params.get("album_name"),
            use_quota=bool(params.get("use_quota", False)),
            saver=bool(params.get("saver", False)),
            recursive=recursive,
            show_progress=bool(params.get("show_progress", False)),
            threads=int(params.get("threads", 1)),
            force_upload=bool(params.get("force_upload", False)),
            delete_from_host=bool(params.get("delete_from_host", False)),
            filter_exp=params.get("filter_exp", ""),
            filter_exclude=bool(params.get("filter_exclude", False)),
            filter_regex=bool(params.get("filter_regex", False)),
            filter_ignore_case=bool(params.get("filter_ignore_case", False)),
            filter_path=bool(params.get("filter_path", False)),
        )
        progress(1.0, "Upload completed")
        return {"operation": "upload", "uploaded": result, "uploaded_count": len(result)}

    if op == "move_to_trash":
        hashes = params.get("sha1_hashes")
        if not hashes:
            raise ValueError("gpmc.move_to_trash requires params.sha1_hashes")
        if dry_run:
            count = len(hashes) if isinstance(hashes, list) else 1
            return {"operation": "move_to_trash", "target_count": count}
        if not auth_data:
            raise RuntimeError("gpmc auth_data is missing for this account")
        try:
            from gpmc import Client  # type: ignore
        except Exception as exc:
            raise RuntimeError("gpmc is not installed. Install package before running gpmc jobs.") from exc

        progress(0.5, "Submitting move_to_trash request")
        client = Client(auth_data=auth_data)
        response = client.move_to_trash(hashes)
        progress(1.0, "move_to_trash completed")
        return {"operation": "move_to_trash", "response": response}

    if op == "get_media_key_by_hash":
        sha1_hash = params.get("sha1_hash")
        if not sha1_hash:
            raise ValueError("gpmc.get_media_key_by_hash requires params.sha1_hash")
        if dry_run:
            return {"operation": "get_media_key_by_hash", "sha1_hash": sha1_hash}
        if not auth_data:
            raise RuntimeError("gpmc auth_data is missing for this account")
        try:
            from gpmc import Client  # type: ignore
        except Exception as exc:
            raise RuntimeError("gpmc is not installed. Install package before running gpmc jobs.") from exc
        progress(0.5, "Checking hash in remote library")
        client = Client(auth_data=auth_data)
        media_key = client.get_media_key_by_hash(sha1_hash)
        progress(1.0, "Lookup completed")
        return {"operation": "get_media_key_by_hash", "sha1_hash": sha1_hash, "media_key": media_key}

    if op == "add_to_album":
        media_keys = params.get("media_keys")
        album_name = params.get("album_name")
        if not media_keys or not album_name:
            raise ValueError("gpmc.add_to_album requires params.media_keys and params.album_name")
        if dry_run:
            return {"operation": "add_to_album", "target_count": len(media_keys), "album_name": album_name}

        if not auth_data:
            raise RuntimeError("gpmc auth_data is missing for this account")
        try:
            from gpmc import Client  # type: ignore
        except Exception as exc:
            raise RuntimeError("gpmc is not installed. Install package before running gpmc jobs.") from exc

        progress(0.5, "Adding media to album")
        client = Client(auth_data=auth_data)
        created_album_keys = client.add_to_album(media_keys=media_keys, album_name=album_name, show_progress=bool(params.get("show_progress", False)))
        progress(1.0, "add_to_album completed")
        return {"operation": "add_to_album", "album_keys": created_album_keys}

    if op == "update_cache":
        if dry_run:
            return {"operation": "update_cache", "note": "cache update would run"}

        if not auth_data:
            raise RuntimeError("gpmc auth_data is missing for this account")
        try:
            from gpmc import Client  # type: ignore
        except Exception as exc:
            raise RuntimeError("gpmc is not installed. Install package before running gpmc jobs.") from exc

        progress(0.5, "Updating local cache")
        client = Client(auth_data=auth_data)
        client.update_cache(show_progress=bool(params.get("show_progress", True)))
        progress(1.0, "update_cache completed")
        return {"operation": "update_cache", "status": "ok"}

    raise ValueError(f"Unsupported gpmc operation: {operation}")
