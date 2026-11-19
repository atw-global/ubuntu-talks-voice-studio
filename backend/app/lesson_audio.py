"""Byte-range slicing for private lesson MP3 responses.

The browser, especially mobile Safari, issues many Range requests.
Slicing a verified buffer avoids a new storage read for every range.
"""
from __future__ import annotations

import re


def clip_audio(blob: bytes, range_header: str | None) -> tuple[int, bytes, dict]:
    """Return HTTP status, body, and extra headers for a verified MP3."""
    total = len(blob)
    raw = (range_header or "").strip()
    if not raw:
        return 200, blob, {}
    found = re.fullmatch(r"bytes=(\d*)-(\d*)", raw)
    if not found or not (found.group(1) or found.group(2)):
        return 416, b"", {"Content-Range": f"bytes */{total}"}
    first, last = found.groups()
    if first:
        start = int(first)
        stop = int(last) if last else total - 1
    else:
        suffix = int(last)
        if suffix == 0:
            return 416, b"", {"Content-Range": f"bytes */{total}"}
        start = max(0, total - suffix)
        stop = total - 1
    stop = min(stop, total - 1)
    if start >= total or start > stop:
        return 416, b"", {"Content-Range": f"bytes */{total}"}
    return 206, blob[start:stop + 1], {"Content-Range": f"bytes {start}-{stop}/{total}"}
