from __future__ import annotations

import glob
from pathlib import Path
from typing import Any

from .common import AdapterResult, ProgressFn


def _expand_patterns(patterns: list[str]) -> list[Path]:
    files: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.exists():
            files.append(path)
            continue
        matches = glob.glob(pattern, recursive=True)
        files.extend([Path(match) for match in matches if Path(match).is_file()])
    unique: dict[str, Path] = {f.resolve().as_posix(): f for f in files}
    return list(unique.values())


def run(operation: str, params: dict[str, Any], dry_run: bool, progress: ProgressFn) -> AdapterResult:
    op = operation.replace("gp_disguise.", "")
    patterns = params.get("files")
    if not patterns or not isinstance(patterns, list):
        raise ValueError("gp_disguise requires params.files as a list of file paths/patterns")

    files = _expand_patterns(patterns)
    if not files:
        raise ValueError("No matching files were found")

    if op == "hide":
        media_type = params.get("type", "image")
        is_video = media_type == "video"
        separator = str(params.get("separator", "FILE_DATA_BEGIN"))
        output = params.get("output")

        if dry_run:
            return {
                "operation": "hide",
                "target_count": len(files),
                "type": media_type,
                "sample": [f.as_posix() for f in files[:10]],
            }

        try:
            from gp_disguise import Config, MediaHider  # type: ignore
        except Exception as exc:
            raise RuntimeError("gp_disguise is not installed. Install package before running disguise jobs.") from exc

        progress(0.2, "Starting hide operation")
        config = Config(is_video=is_video, separator=separator.encode("utf-8"))
        hider = MediaHider(config)
        outputs: list[str] = []

        for idx, file in enumerate(files, start=1):
            out_path = Path(output) if output else None
            created = hider.hide_file(file, out_path)
            outputs.append(created.as_posix())
            progress(0.2 + 0.8 * (idx / len(files)), f"Processed {idx}/{len(files)}")

        return {"operation": "hide", "created": outputs, "created_count": len(outputs)}

    if op == "extract":
        separator = str(params.get("separator", "FILE_DATA_BEGIN"))
        suffix = str(params.get("suffix", ".restored"))
        output = params.get("output")

        if dry_run:
            return {
                "operation": "extract",
                "target_count": len(files),
                "sample": [f.as_posix() for f in files[:10]],
            }

        try:
            from gp_disguise import Config, MediaExtractor  # type: ignore
        except Exception as exc:
            raise RuntimeError("gp_disguise is not installed. Install package before running disguise jobs.") from exc

        progress(0.2, "Starting extract operation")
        config = Config(separator=separator.encode("utf-8"), restored_suffix=suffix)
        extractor = MediaExtractor(config)
        outputs: list[str] = []

        for idx, file in enumerate(files, start=1):
            out_dir = Path(output) if output else None
            created = extractor.extract_file(file, out_dir)
            outputs.append(created.as_posix())
            progress(0.2 + 0.8 * (idx / len(files)), f"Processed {idx}/{len(files)}")

        return {"operation": "extract", "created": outputs, "created_count": len(outputs)}

    raise ValueError(f"Unsupported gp_disguise operation: {operation}")
