from __future__ import annotations

from typing import Any


# Netscape cookie file format parser
# domain\tinclude_subdomains\tpath\tsecure\texpiry\tname\tvalue

def parse_netscape_cookie_file(raw: str) -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#HttpOnly_"):
            stripped = stripped.replace("#HttpOnly_", "", 1)
        elif stripped.startswith("#"):
            continue

        parts = stripped.split("\t")
        if len(parts) != 7:
            continue

        domain, include_subdomains, path, secure, expiry, name, value = parts
        if not name:
            continue

        try:
            expires_at = int(expiry)
        except ValueError:
            expires_at = 0

        cookies.append(
            {
                "domain": domain,
                "include_subdomains": include_subdomains.upper() == "TRUE",
                "path": path,
                "secure": secure.upper() == "TRUE",
                "expires_at": expires_at,
                "name": name,
                "value": value,
            }
        )
    return cookies


def cookie_header(cookies: list[dict[str, Any]]) -> str:
    return "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies if cookie.get("name")])


def parse_cookie_string(raw: str, domain: str = ".google.com") -> list[dict[str, Any]]:
    cookies: list[dict[str, Any]] = []
    for part in raw.split(";"):
        segment = part.strip()
        if not segment or "=" not in segment:
            continue
        name, value = segment.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        cookies.append(
            {
                "domain": domain,
                "include_subdomains": True,
                "path": "/",
                "secure": True,
                "expires_at": 0,
                "name": name,
                "value": value,
            }
        )
    return cookies
