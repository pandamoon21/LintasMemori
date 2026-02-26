from __future__ import annotations

import glob
import mimetypes
from pathlib import Path


def expand_patterns(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            files.extend([item for item in path.rglob("*") if item.is_file()])
            continue
        files.extend([Path(match) for match in glob.glob(pattern, recursive=True) if Path(match).is_file()])
    dedup: dict[str, Path] = {}
    for item in files:
        try:
            dedup[item.resolve().as_posix()] = item
        except OSError:
            dedup[item.as_posix()] = item
    return list(dedup.values())


def collect_media_files(target: str | list[str], recursive: bool = False) -> list[Path]:
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

    media: list[Path] = []
    for file in files:
        mime, _ = mimetypes.guess_type(file.as_posix())
        if mime and (mime.startswith("image/") or mime.startswith("video/")):
            media.append(file)
    return media
