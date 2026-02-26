from __future__ import annotations

from typing import Any

from .adapters.gptk_methods import catalog_entries as gptk_catalog_entries


def catalog_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = [
        {
            "provider": "gpmc",
            "operation": "gpmc.upload",
            "description": "Upload media from file/folder target.",
            "params_template": {
                "target": ".",
                "recursive": False,
                "threads": 1,
                "album_name": None,
                "use_quota": False,
                "saver": False,
                "force_upload": False,
                "delete_from_host": False,
                "filter_exp": "",
                "filter_exclude": False,
                "filter_regex": False,
                "filter_ignore_case": False,
                "filter_path": False,
            },
            "destructive": False,
            "notes": ["Equivalent to gpmc CLI upload."],
        },
        {
            "provider": "gpmc",
            "operation": "gpmc.move_to_trash",
            "description": "Move remote media to trash by SHA1 hashes.",
            "params_template": {"sha1_hashes": []},
            "destructive": True,
            "notes": ["Set dry-run first, then confirmed run."],
        },
        {
            "provider": "gpmc",
            "operation": "gpmc.add_to_album",
            "description": "Add media keys into an album.",
            "params_template": {"media_keys": [], "album_name": "Album Name", "show_progress": False},
            "destructive": False,
            "notes": [],
        },
        {
            "provider": "gpmc",
            "operation": "gpmc.get_media_key_by_hash",
            "description": "Lookup a media key by SHA1 hash.",
            "params_template": {"sha1_hash": ""},
            "destructive": False,
            "notes": [],
        },
        {
            "provider": "gpmc",
            "operation": "gpmc.update_cache",
            "description": "Sync/update local gpmc cache database.",
            "params_template": {"show_progress": True},
            "destructive": False,
            "notes": [],
        },
        {
            "provider": "gp_disguise",
            "operation": "gp_disguise.hide",
            "description": "Hide files into image/video containers.",
            "params_template": {"files": ["*.txt"], "type": "image", "output": None, "separator": "FILE_DATA_BEGIN"},
            "destructive": False,
            "notes": ["For video mode, ensure ffmpeg installed."],
        },
        {
            "provider": "gp_disguise",
            "operation": "gp_disguise.extract",
            "description": "Extract hidden payloads from media containers.",
            "params_template": {"files": ["*.bmp", "*.mp4"], "output": None, "separator": "FILE_DATA_BEGIN", "suffix": ".restored"},
            "destructive": False,
            "notes": [],
        },
        {
            "provider": "gptk",
            "operation": "gptk.rpc_execute",
            "description": "Advanced: execute arbitrary GPTK RPC manually.",
            "params_template": {"rpcid": "EzwWhf", "requestData": [], "sourcePath": "/", "forceBootstrap": False},
            "destructive": False,
            "notes": ["Use when operation is not covered by presets."],
        },
    ]

    entries.extend(gptk_catalog_entries())
    return sorted(entries, key=lambda entry: (entry["provider"], entry["operation"]))
