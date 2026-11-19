"""Byte-range slicing and spoken-cue alignment for private lesson MP3 responses.

The browser, especially mobile Safari, issues many Range requests.
Slicing a verified buffer avoids a new storage read for every range.
"""
from __future__ import annotations

import array
import re
import sys


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


def align_spoken_cues(pcm: bytes, sample_rate: int, cues: list[dict]) -> list[dict] | None:
    """Place each cue on a detected spoken burst.

    Stored MP3 timestamps can sit ahead of the voice after a concat export.
    A short breath inside one line is joined when the gap is shorter than the
    pause written between lines. This returns a new cue list only when the
    recording then separates into the same number of lines. A mismatch keeps
    the stored timings.
    """
    regions = _join_short_gaps(_speech_regions(pcm, sample_rate), len(cues))
    if len(regions) != len(cues) or not cues:
        return None
    aligned = []
    for cue, (start, end) in zip(cues, regions):
        if end <= start:
            return None
        updated = dict(cue)
        updated["start"] = round(start, 3)
        updated["end"] = round(end, 3)
        aligned.append(updated)
    return aligned


def apply_timing_result(manifest: dict, aligned: list[dict] | None) -> dict:
    """Keep stored times when speech detection does not match, and mark them unconfirmed."""
    served = dict(manifest)
    source = aligned if aligned else list(manifest.get("cues") or [])
    cues = []
    for cue in source:
        item = dict(cue)
        item["timing_status"] = "speech_onset_aligned" if aligned else "manual_review"
        cues.append(item)
    served["cues"] = cues
    if aligned:
        served["timing_method"] = "speech_onset_aligned_to_verified_mp3"
        served["timing_review_required"] = False
    else:
        served["timing_method"] = "stored_timestamps_require_manual_review"
        served["timing_review_required"] = True
    return served


def _speech_regions(pcm: bytes, sample_rate: int) -> list[tuple[float, float]]:
    if sample_rate <= 0 or len(pcm) < 4:
        return []
    samples = array.array("h")
    usable = len(pcm) - (len(pcm) % 2)
    samples.frombytes(pcm[:usable])
    if sys.byteorder == "big":
        samples.byteswap()
    hop = max(1, sample_rate // 100)
    window = max(hop, sample_rate // 50)
    if len(samples) < window:
        return []
    loudness = []
    index = 0
    while index + window <= len(samples):
        energy = 0
        for value in samples[index:index + window]:
            energy += value * value
        loudness.append((energy / window) ** 0.5)
        index += hop
    peak = max(loudness) if loudness else 0
    if peak < 500:
        return []
    threshold = max(400.0, peak * 0.18)
    regions: list[tuple[float, float]] = []
    active = False
    start = 0.0
    for frame, level in enumerate(loudness):
        moment = frame * hop / sample_rate
        if level >= threshold and not active:
            active = True
            start = moment
        elif level < threshold and active:
            active = False
            end = moment
            if end - start >= 0.12:
                regions.append((start, end))
    if active:
        end = len(samples) / sample_rate
        if end - start >= 0.12:
            regions.append((start, end))
    merged: list[tuple[float, float]] = []
    for start, end in regions:
        if merged and start - merged[-1][1] < 0.18:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _join_short_gaps(regions: list[tuple[float, float]], expected: int) -> list[tuple[float, float]]:
    """Join splits inside one line. Never cross the pause between lines."""
    joined = list(regions)
    while len(joined) > expected > 0:
        gaps = [
            (joined[index + 1][0] - joined[index][1], index)
            for index in range(len(joined) - 1)
        ]
        gap, index = min(gaps)
        if gap >= 0.32:
            break
        joined[index] = (joined[index][0], joined[index + 1][1])
        del joined[index + 1]
    return joined
