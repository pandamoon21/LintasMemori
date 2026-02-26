from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


RequestBuilder = Callable[[dict[str, Any]], list[Any]]


@dataclass(frozen=True)
class GptkMethodDef:
    operation: str
    rpcid: str
    description: str
    params_template: dict[str, Any]
    request_builder: RequestBuilder
    destructive: bool = False
    source_path_hint: str = "/"


# Request builders mirror the original Google-Photos-Toolkit api.ts method payloads.
METHODS: dict[str, GptkMethodDef] = {}


def _register(defn: GptkMethodDef) -> None:
    METHODS[defn.operation] = defn


_register(
    GptkMethodDef(
        operation="get_items_by_taken_date",
        rpcid="lcxiM",
        description="List media by taken date timeline.",
        params_template={"timestamp": None, "source": None, "pageId": None, "pageSize": 500},
        request_builder=lambda p: [p.get("pageId"), p.get("timestamp"), int(p.get("pageSize", 500)), None, 1, {"library": 1, "archive": 2}.get(p.get("source"), 3)],
    )
)

_register(
    GptkMethodDef(
        operation="get_items_by_uploaded_date",
        rpcid="EzkLib",
        description="List media by upload date.",
        params_template={"pageId": None},
        request_builder=lambda p: ["", [[4, "ra", 0, 0]], p.get("pageId")],
    )
)

_register(
    GptkMethodDef(
        operation="search",
        rpcid="EzkLib",
        description="Search media library.",
        params_template={"searchQuery": "cats", "pageId": None},
        request_builder=lambda p: [p.get("searchQuery", ""), None, p.get("pageId")],
    )
)

_register(
    GptkMethodDef(
        operation="get_remote_matches_by_hash",
        rpcid="swbisb",
        description="Find remote items by hash list.",
        params_template={"hashArray": []},
        request_builder=lambda p: [p.get("hashArray", []), None, 3, 0],
    )
)

_register(
    GptkMethodDef(
        operation="get_favorite_items",
        rpcid="EzkLib",
        description="List favorite items.",
        params_template={"pageId": None},
        request_builder=lambda p: ["Favorites", [[5, "8", 0, 9]], p.get("pageId")],
    )
)

_register(
    GptkMethodDef(
        operation="get_trash_items",
        rpcid="zy0IHe",
        description="List trash items.",
        params_template={"pageId": None},
        request_builder=lambda p: [p.get("pageId")],
    )
)

_register(
    GptkMethodDef(
        operation="get_locked_folder_items",
        rpcid="nMFwOc",
        description="List locked folder items.",
        params_template={"pageId": None, "sourcePath": "/u/0/photos/lockedfolder"},
        request_builder=lambda p: [p.get("pageId")],
        source_path_hint="/u/0/photos/lockedfolder",
    )
)

_register(
    GptkMethodDef(
        operation="move_items_to_trash",
        rpcid="XwAOJf",
        description="Move items to trash by dedup keys.",
        params_template={"dedupKeyArray": []},
        request_builder=lambda p: [None, 1, p.get("dedupKeyArray", []), 3],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="restore_from_trash",
        rpcid="XwAOJf",
        description="Restore trashed items by dedup keys.",
        params_template={"dedupKeyArray": []},
        request_builder=lambda p: [None, 3, p.get("dedupKeyArray", []), 2],
    )
)

_register(
    GptkMethodDef(
        operation="get_shared_links",
        rpcid="F2A0H",
        description="List shared links.",
        params_template={"pageId": None},
        request_builder=lambda p: [p.get("pageId"), None, 2, None, 3],
    )
)

_register(
    GptkMethodDef(
        operation="get_albums",
        rpcid="Z5xsfc",
        description="List albums.",
        params_template={"pageId": None, "pageSize": 100},
        request_builder=lambda p: [p.get("pageId"), None, None, None, 1, None, None, int(p.get("pageSize", 100)), [2], 5],
    )
)

_register(
    GptkMethodDef(
        operation="get_album_page",
        rpcid="snAcKc",
        description="List album or shared-link page.",
        params_template={"albumMediaKey": "", "pageId": None, "authKey": None},
        request_builder=lambda p: [p.get("albumMediaKey"), p.get("pageId"), None, p.get("authKey")],
    )
)

_register(
    GptkMethodDef(
        operation="remove_items_from_album",
        rpcid="ycV3Nd",
        description="Remove items from album by item-album keys.",
        params_template={"itemAlbumMediaKeyArray": []},
        request_builder=lambda p: [p.get("itemAlbumMediaKeyArray", [])],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="create_album",
        rpcid="OXvT9d",
        description="Create a new album.",
        params_template={"albumName": "New Album"},
        request_builder=lambda p: [p.get("albumName", "New Album"), None, 2],
    )
)

_register(
    GptkMethodDef(
        operation="add_items_to_album",
        rpcid="E1Cajb",
        description="Add items to an album or create one by name.",
        params_template={"mediaKeyArray": [], "albumMediaKey": None, "albumName": None},
        request_builder=lambda p: ([p.get("mediaKeyArray", []), None, p.get("albumName")] if p.get("albumName") else [p.get("mediaKeyArray", []), p.get("albumMediaKey")]),
    )
)

_register(
    GptkMethodDef(
        operation="add_items_to_shared_album",
        rpcid="laUYf",
        description="Add items to shared album.",
        params_template={"mediaKeyArray": [], "albumMediaKey": None, "albumName": None},
        request_builder=lambda p: ([p.get("mediaKeyArray", []), None, p.get("albumName")] if p.get("albumName") else [p.get("albumMediaKey"), [2, None, [ [[id]] for id in p.get("mediaKeyArray", []) ], None, None, None, [1]]]),
    )
)

_register(
    GptkMethodDef(
        operation="set_album_item_order",
        rpcid="QD9nKf",
        description="Reorder items in album.",
        params_template={"albumMediaKey": "", "albumItemKeys": [], "insertAfter": None},
        request_builder=lambda p: (
            [p.get("albumMediaKey"), None, 3, None, [[[item]] for item in p.get("albumItemKeys", [])], [[p.get("insertAfter")]]]
            if p.get("insertAfter")
            else [p.get("albumMediaKey"), None, 1, None, [[[item]] for item in p.get("albumItemKeys", [])]]
        ),
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="set_favorite",
        rpcid="Ftfh0",
        description="Set favorite/unfavorite by dedup keys.",
        params_template={"dedupKeyArray": [], "action": True},
        request_builder=lambda p: [[ [None, item] for item in p.get("dedupKeyArray", []) ], [1 if p.get("action", True) else 2]],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="set_archive",
        rpcid="w7TP3c",
        description="Set archive/unarchive by dedup keys.",
        params_template={"dedupKeyArray": [], "action": True},
        request_builder=lambda p: [[ [None, [1 if p.get("action", True) else 2], [None, item]] for item in p.get("dedupKeyArray", []) ], None, 1],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="move_to_locked_folder",
        rpcid="StLnCe",
        description="Move items to locked folder.",
        params_template={"dedupKeyArray": [], "sourcePath": "/u/0/photos/lockedfolder"},
        request_builder=lambda p: [p.get("dedupKeyArray", []), []],
        destructive=True,
        source_path_hint="/u/0/photos/lockedfolder",
    )
)

_register(
    GptkMethodDef(
        operation="remove_from_locked_folder",
        rpcid="Pp2Xxe",
        description="Move items out of locked folder.",
        params_template={"dedupKeyArray": [], "sourcePath": "/u/0/photos/lockedfolder"},
        request_builder=lambda p: [p.get("dedupKeyArray", [])],
        destructive=True,
        source_path_hint="/u/0/photos/lockedfolder",
    )
)

_register(
    GptkMethodDef(
        operation="get_storage_quota",
        rpcid="EzwWhf",
        description="Get account storage quota.",
        params_template={},
        request_builder=lambda _p: [],
    )
)

_register(
    GptkMethodDef(
        operation="get_download_url",
        rpcid="pLFTfd",
        description="Get download URLs for media keys.",
        params_template={"mediaKeyArray": [], "authKey": None},
        request_builder=lambda p: [p.get("mediaKeyArray", []), None, p.get("authKey")],
    )
)

_register(
    GptkMethodDef(
        operation="get_download_token",
        rpcid="yCLA7",
        description="Request download token for bulk zip.",
        params_template={"mediaKeyArray": []},
        request_builder=lambda p: [[[id] for id in p.get("mediaKeyArray", [])]],
    )
)

_register(
    GptkMethodDef(
        operation="check_download_token",
        rpcid="dnv2s",
        description="Poll download token status.",
        params_template={"dlToken": ""},
        request_builder=lambda p: [[p.get("dlToken")]],
    )
)

_register(
    GptkMethodDef(
        operation="remove_items_from_shared_album",
        rpcid="LjmOue",
        description="Remove items from shared album.",
        params_template={"albumMediaKey": "", "mediaKeyArray": []},
        request_builder=lambda p: [[p.get("albumMediaKey")], [p.get("mediaKeyArray", [])], [[None, None, None, [None, [], []], None, None, None, None, None, None, None, None, None, []]]],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="save_shared_media_to_library",
        rpcid="V8RKJ",
        description="Save shared-album media to own library.",
        params_template={"albumMediaKey": "", "mediaKeyArray": []},
        request_builder=lambda p: [p.get("mediaKeyArray", []), None, p.get("albumMediaKey")],
    )
)

_register(
    GptkMethodDef(
        operation="save_partner_shared_media_to_library",
        rpcid="Es7fke",
        description="Save partner-shared media to own library.",
        params_template={"mediaKeyArray": []},
        request_builder=lambda p: [[[id] for id in p.get("mediaKeyArray", [])]],
    )
)

_register(
    GptkMethodDef(
        operation="get_partner_shared_media",
        rpcid="e9T5je",
        description="Get partner shared media page.",
        params_template={"partnerActorId": "", "gaiaId": "", "pageId": None},
        request_builder=lambda p: [p.get("pageId"), None, [None, [[[2, 1]]], [p.get("partnerActorId")], [None, p.get("gaiaId")], 1]],
    )
)

_register(
    GptkMethodDef(
        operation="set_item_geo_data",
        rpcid="EtUHOe",
        description="Set geolocation on items.",
        params_template={
            "dedupKeyArray": [],
            "center": [0, 0],
            "visible1": [0, 0],
            "visible2": [0, 0],
            "scale": 10,
            "gMapsPlaceId": "",
        },
        request_builder=lambda p: [[ [None, key] for key in p.get("dedupKeyArray", []) ], [2, p.get("center", [0, 0]), [p.get("visible1", [0, 0]), p.get("visible2", [0, 0])], [None, None, p.get("scale", 10)], p.get("gMapsPlaceId", "")]],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="delete_item_geo_data",
        rpcid="EtUHOe",
        description="Delete geolocation from items.",
        params_template={"dedupKeyArray": []},
        request_builder=lambda p: [[ [None, key] for key in p.get("dedupKeyArray", []) ], [1]],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="set_items_timestamp",
        rpcid="DaSgWe",
        description="Bulk set timestamp for items.",
        params_template={"items": [{"dedupKey": "", "timestampSec": 0, "timezoneSec": 0}]},
        request_builder=lambda p: [[ [item.get("dedupKey"), item.get("timestampSec"), item.get("timezoneSec")] for item in p.get("items", []) ]],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="set_item_description",
        rpcid="AQNOFd",
        description="Set item description.",
        params_template={"dedupKey": "", "description": ""},
        request_builder=lambda p: [None, p.get("description", ""), p.get("dedupKey")],
        destructive=True,
    )
)

_register(
    GptkMethodDef(
        operation="get_item_info",
        rpcid="VrseUb",
        description="Get item basic info.",
        params_template={"mediaKey": "", "albumMediaKey": None, "authKey": None},
        request_builder=lambda p: [p.get("mediaKey"), None, p.get("authKey"), None, p.get("albumMediaKey")],
    )
)

_register(
    GptkMethodDef(
        operation="get_item_info_ext",
        rpcid="fDcn4b",
        description="Get item extended info.",
        params_template={"mediaKey": "", "authKey": None},
        request_builder=lambda p: [p.get("mediaKey"), 1, p.get("authKey"), None, 1],
    )
)

_register(
    GptkMethodDef(
        operation="get_batch_media_info",
        rpcid="EWgK9e",
        description="Get batch media info for media keys.",
        params_template={"mediaKeyArray": []},
        request_builder=lambda p: [[[ [[id] for id in p.get("mediaKeyArray", [])] ], [[None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, [], None, None, None, None, None, None, None, None, None, None, []]]]],
    )
)


def resolve_method(operation: str) -> GptkMethodDef:
    normalized = operation.replace("gptk.", "").strip()
    if normalized not in METHODS:
        supported = ", ".join(sorted(f"gptk.{name}" for name in METHODS))
        raise ValueError(f"Unsupported gptk operation: {operation}. Supported: {supported}")
    return METHODS[normalized]


def catalog_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for method in METHODS.values():
        entries.append(
            {
                "provider": "gptk",
                "operation": f"gptk.{method.operation}",
                "description": method.description,
                "params_template": method.params_template,
                "destructive": method.destructive,
                "notes": [
                    "Returns raw RPC payload.",
                    f"rpcid={method.rpcid}",
                    f"sourcePath hint: {method.source_path_hint}",
                ],
            }
        )
    return sorted(entries, key=lambda x: x["operation"])
