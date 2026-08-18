"""Deterministic feed scoring and diversity helpers.

Database access stays in the route layer so these rules remain cheap to unit test.
"""
from __future__ import annotations

import base64
import json
import math
from datetime import datetime


def score_post(*, created_at: datetime, reactions: int, comments: int,
               is_friend: bool, is_following: bool, is_favorite: bool,
               viewer_interacted: bool, show_fewer_author: bool,
               now: datetime | None = None) -> float:
    now = now or datetime.utcnow()
    age_hours = max(0.0, (now - created_at).total_seconds() / 3600)
    recency = 6.0 * math.exp(-age_hours / 36.0)
    relationship = (3.5 if is_friend else 0.0) + (2.0 if is_following else 0.0) + (5.0 if is_favorite else 0.0)
    engagement = math.log1p(reactions) * 1.2 + math.log1p(comments) * 1.6
    return round(recency + relationship + engagement + (1.5 if viewer_interacted else 0.0) - (5.0 if show_fewer_author else 0.0), 6)


def diversify(items: list[dict], limit: int, max_per_author: int | None = None) -> list[dict]:
    """Prevent one author and repeated shares of one source from flooding a page."""
    if limit <= 0:
        return []
    max_per_author = max_per_author or max(2, math.ceil(limit / 3))
    chosen, deferred, author_counts, shared_sources = [], [], {}, set()
    for item in items:
        author_id = item["author_id"]
        source_id = item.get("shared_post_id")
        duplicate_source = source_id is not None and source_id in shared_sources
        repeated_author = author_counts.get(author_id, 0) >= max_per_author
        consecutive = len(chosen) >= 2 and chosen[-1]["author_id"] == author_id == chosen[-2]["author_id"]
        if duplicate_source or repeated_author or consecutive:
            deferred.append(item)
            continue
        chosen.append(item)
        author_counts[author_id] = author_counts.get(author_id, 0) + 1
        if source_id is not None:
            shared_sources.add(source_id)
        if len(chosen) == limit:
            return chosen
    for item in deferred:
        if item["id"] not in {row["id"] for row in chosen}:
            chosen.append(item)
        if len(chosen) == limit:
            break
    return chosen


def encode_cursor(seen_ids: list[int]) -> str:
    raw = json.dumps({"seen": seen_ids[-300:]}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(value: str | None) -> set[int]:
    if not value:
        return set()
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        values = json.loads(raw).get("seen", [])
        return {int(item) for item in values[:300] if int(item) > 0}
    except (ValueError, TypeError, json.JSONDecodeError):
        return set()
