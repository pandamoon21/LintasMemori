from __future__ import annotations

from typing import Any, Callable, Optional


def _key(obj: Any, key: Any, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        s_key = str(key)
        if s_key in obj:
            return obj[s_key]
        return default
    if isinstance(obj, (list, tuple)) and isinstance(key, int):
        if -len(obj) <= key < len(obj):
            return obj[key]
    return default


def _last(arr: Any) -> Any:
    if isinstance(arr, (list, tuple)) and arr:
        return arr[-1]
    return None


def _map(items: Any, fn: Callable[[Any], Any]) -> list[Any]:
    if not isinstance(items, list):
        return []
    return [fn(item) for item in items]


def _actor_parse(data: Any) -> dict[str, Any]:
    return {
        "actorId": _key(data, 0),
        "gaiaId": _key(data, 1),
        "name": _key(_key(data, 11), 0),
        "gender": _key(_key(data, 11), 2),
        "profilePhotoUrl": _key(_key(data, 12), 0),
    }


def _library_item_parse(item_data: Any) -> dict[str, Any]:
    tail = _last(item_data)
    nested_geo = _key(_key(_key(_key(_key(_key(tail, 129168200), 1), 4), 0), 1), 0)
    return {
        "mediaKey": _key(item_data, 0),
        "timestamp": _key(item_data, 2),
        "timezoneOffset": _key(item_data, 4),
        "creationTimestamp": _key(item_data, 5),
        "dedupKey": _key(item_data, 3),
        "thumb": _key(_key(item_data, 1), 0),
        "resWidth": _key(_key(item_data, 1), 1),
        "resHeight": _key(_key(item_data, 1), 2),
        "isPartialUpload": _key(_key(item_data, 12), 0) == 20,
        "isArchived": bool(_key(item_data, 13, False)),
        "isFavorite": _key(_key(tail, 163238866), 0),
        "duration": _key(_key(tail, 76647426), 0),
        "descriptionShort": _key(_key(tail, 396644657), 0),
        "isLivePhoto": _key(tail, 146008172) is not None,
        "livePhotoDuration": _key(_key(tail, 146008172), 1),
        "geoLocation": {
            "coordinates": _key(_key(_key(tail, 129168200), 1), 0),
            "name": _key(nested_geo, 0),
        },
    }


def _locked_folder_item_parse(item_data: Any) -> dict[str, Any]:
    tail = _last(item_data)
    return {
        "mediaKey": _key(item_data, 0),
        "timestamp": _key(item_data, 2),
        "creationTimestamp": _key(item_data, 5),
        "dedupKey": _key(item_data, 3),
        "duration": _key(_key(tail, 76647426), 0),
    }


def _album_parse(item_data: Any) -> dict[str, Any]:
    tail = _last(item_data)
    meta = _key(tail, 72930366)
    return {
        "mediaKey": _key(item_data, 0),
        "ownerActorId": _key(_key(item_data, 6), 0),
        "title": _key(meta, 1),
        "thumb": _key(_key(item_data, 1), 0),
        "itemCount": _key(meta, 3),
        "creationTimestamp": _key(_key(meta, 2), 4),
        "modifiedTimestamp": _key(_key(meta, 2), 9),
        "timestampRange": [_key(_key(meta, 2), 5), _key(_key(meta, 2), 6)],
        "isShared": bool(_key(meta, 4, False)),
    }


def _album_item_parse(item_data: Any) -> dict[str, Any]:
    tail = _last(item_data)
    return {
        "mediaKey": _key(item_data, 0),
        "thumb": _key(_key(item_data, 1), 0),
        "resWidth": _key(_key(item_data, 1), 1),
        "resHeight": _key(_key(item_data, 1), 2),
        "timestamp": _key(item_data, 2),
        "timezoneOffset": _key(item_data, 4),
        "creationTimestamp": _key(item_data, 5),
        "dedupKey": _key(item_data, 3),
        "isLivePhoto": _key(tail, 146008172) is not None,
        "livePhotoDuration": _key(_key(tail, 146008172), 1),
        "duration": _key(_key(tail, 76647426), 0),
    }


def _trash_item_parse(item_data: Any) -> dict[str, Any]:
    tail = _last(item_data)
    return {
        "mediaKey": _key(item_data, 0),
        "thumb": _key(_key(item_data, 1), 0),
        "resWidth": _key(_key(item_data, 1), 1),
        "resHeight": _key(_key(item_data, 1), 2),
        "timestamp": _key(item_data, 2),
        "timezoneOffset": _key(item_data, 4),
        "creationTimestamp": _key(item_data, 5),
        "dedupKey": _key(item_data, 3),
        "duration": _key(_key(tail, 76647426), 0),
    }


def _bulk_media_info_item_parse(item_data: Any) -> dict[str, Any]:
    info = _key(item_data, 1)
    tail = _last(info)
    takes_up_space = _key(tail, 0)
    orig_quality = _key(tail, 2)
    return {
        "mediaKey": _key(item_data, 0),
        "descriptionFull": _key(info, 2),
        "fileName": _key(info, 3),
        "timestamp": _key(info, 6),
        "timezoneOffset": _key(info, 7),
        "creationTimestamp": _key(info, 8),
        "size": _key(info, 9),
        "takesUpSpace": None if takes_up_space is None else takes_up_space == 1,
        "spaceTaken": _key(tail, 1),
        "isOriginalQuality": None if orig_quality is None else orig_quality == 2,
    }


def _library_timeline_page(data: Any) -> dict[str, Any]:
    return {
        "items": _map(_key(data, 0), _library_item_parse),
        "nextPageId": _key(data, 1),
        "lastItemTimestamp": int(_key(data, 2, 0) or 0),
    }


def _library_generic_page(data: Any) -> dict[str, Any]:
    return {
        "items": _map(_key(data, 0), _library_item_parse),
        "nextPageId": _key(data, 1),
    }


def _locked_folder_page(data: Any) -> dict[str, Any]:
    return {
        "nextPageId": _key(data, 0),
        "items": _map(_key(data, 1), _locked_folder_item_parse),
    }


def _links_page(data: Any) -> dict[str, Any]:
    return {
        "items": _map(
            _key(data, 0),
            lambda item: {"mediaKey": _key(item, 6), "linkId": _key(item, 17), "itemCount": _key(item, 3)},
        ),
        "nextPageId": _key(data, 1),
    }


def _albums_page(data: Any) -> dict[str, Any]:
    return {
        "items": _map(_key(data, 0), _album_parse),
        "nextPageId": _key(data, 1),
    }


def _album_items_page(data: Any) -> dict[str, Any]:
    meta = _key(data, 3)
    return {
        "items": _map(_key(data, 1), _album_item_parse),
        "nextPageId": _key(data, 2),
        "mediaKey": _key(meta, 0),
        "title": _key(meta, 1),
        "owner": _actor_parse(_key(meta, 5)),
        "itemCount": _key(meta, 21),
        "authKey": _key(meta, 19),
        "members": _map(_key(meta, 9), _actor_parse),
    }


def _partner_shared_items_page(data: Any) -> dict[str, Any]:
    return {
        "nextPageId": _key(data, 0),
        "items": _map(_key(data, 1), _album_item_parse),
        "members": _map(_key(data, 2), _actor_parse),
        "partnerActorId": _key(data, 4),
        "gaiaId": _key(data, 5),
    }


def _trash_page(data: Any) -> dict[str, Any]:
    return {
        "items": _map(_key(data, 0), _trash_item_parse),
        "nextPageId": _key(data, 1),
    }


def _item_info(data: Any) -> dict[str, Any]:
    media = _key(data, 0)
    meta = _key(media, 15)
    return {
        "mediaKey": _key(media, 0),
        "dedupKey": _key(media, 3),
        "timestamp": _key(media, 2),
        "timezoneOffset": _key(media, 4),
        "creationTimestamp": _key(media, 5),
        "downloadUrl": _key(data, 1),
        "downloadOriginalUrl": _key(data, 7),
        "isArchived": _key(media, 13),
        "isFavorite": _key(_key(meta, 163238866), 0),
        "duration": _key(_key(meta, 76647426), 0),
        "descriptionFull": _key(data, 10),
        "thumb": _key(data, 12),
    }


def _item_info_ext(data: Any) -> dict[str, Any]:
    item0 = _key(data, 0)
    owner = _actor_parse(_key(_key(_key(item0, 27), 4), 0) or _key(item0, 28))
    return {
        "mediaKey": _key(item0, 0),
        "dedupKey": _key(item0, 11),
        "descriptionFull": _key(item0, 1),
        "fileName": _key(item0, 2),
        "timestamp": _key(item0, 3),
        "timezoneOffset": _key(item0, 4),
        "size": _key(item0, 5),
        "resWidth": _key(item0, 6),
        "resHeight": _key(item0, 7),
        "albums": _map(_key(item0, 19), _album_parse),
        "owner": owner,
        "other": _key(item0, 31),
    }


def _bulk_media_info(data: Any) -> list[dict[str, Any]]:
    return _map(data, _bulk_media_info_item_parse)


def _download_token_check(data: Any) -> dict[str, Any]:
    node = _key(_key(_key(_key(_key(data, 0), 0), 0), 2), 0)
    return {
        "fileName": _key(node, 0),
        "downloadUrl": _key(node, 1),
        "downloadSize": _key(node, 2),
        "unzippedSize": _key(node, 3),
    }


def _storage_quota(data: Any) -> dict[str, Any]:
    q = _key(data, 6)
    return {
        "totalUsed": _key(q, 0),
        "totalAvailable": _key(q, 1),
        "usedByGPhotos": _key(q, 3),
    }


def _remote_matches(data: Any) -> list[dict[str, Any]]:
    rows = _key(data, 0)

    def parse_row(row: Any) -> dict[str, Any]:
        item = _key(row, 1)
        return {
            "hash": _key(row, 0),
            "mediaKey": _key(item, 0),
            "thumb": _key(_key(item, 1), 0),
            "resWidth": _key(_key(item, 1), 1),
            "resHeight": _key(_key(item, 1), 2),
            "timestamp": _key(item, 2),
            "dedupKey": _key(item, 3),
            "timezoneOffset": _key(item, 4),
            "creationTimestamp": _key(item, 5),
        }

    return _map(rows, parse_row)


PARSER_REGISTRY: dict[str, Callable[[Any], Any]] = {
    "lcxiM": _library_timeline_page,
    "EzkLib": _library_generic_page,
    "nMFwOc": _locked_folder_page,
    "F2A0H": _links_page,
    "Z5xsfc": _albums_page,
    "snAcKc": _album_items_page,
    "e9T5je": _partner_shared_items_page,
    "zy0IHe": _trash_page,
    "VrseUb": _item_info,
    "fDcn4b": _item_info_ext,
    "EWgK9e": _bulk_media_info,
    "dnv2s": _download_token_check,
    "EzwWhf": _storage_quota,
    "swbisb": _remote_matches,
}


def parse_response(rpcid: str, payload: Any) -> Any:
    if payload is None:
        return None
    parser_fn = PARSER_REGISTRY.get(rpcid)
    if not parser_fn:
        return payload
    try:
        return parser_fn(payload)
    except Exception:
        # Return raw payload when parser can't decode shape.
        return payload
