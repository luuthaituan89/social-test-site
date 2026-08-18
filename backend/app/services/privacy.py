from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import Follow
from ..utils import are_friends, has_restricted
from .policies import post_is_visible

ADVANCED_AUDIENCES = {
    "public", "friends", "friends_except", "specific_friends",
    "followers", "custom", "only_me",
}
PROFILE_FIELDS = {"dob", "hometown", "relationship", "albums", "friends_list"}
PROFILE_DEFAULTS = {
    "dob": {"audience": "friends"},
    "hometown": {"audience": "friends"},
    "relationship": {"audience": "friends"},
    "albums": {"audience": "friends"},
    "friends_list": {"audience": "friends"},
}


def decode_config(raw: str | dict | None) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def normalize_audience_config(config: dict | None) -> dict:
    config = config or {}
    included = sorted({int(value) for value in config.get("included_ids", []) if str(value).isdigit()})
    excluded = sorted({int(value) for value in config.get("excluded_ids", []) if str(value).isdigit()})
    base = config.get("base", "friends")
    if base not in {"public", "friends", "followers"}:
        base = "friends"
    return {"included_ids": included, "excluded_ids": excluded, "base": base}


def encode_audience_config(config: dict | None) -> str | None:
    normalized = normalize_audience_config(config)
    if not normalized["included_ids"] and not normalized["excluded_ids"] and normalized["base"] == "friends":
        return None
    return json.dumps(normalized, separators=(",", ":"))


def is_follower(db: Session, viewer_id: int, owner_id: int) -> bool:
    return db.query(Follow.id).filter(
        Follow.follower_id == viewer_id,
        Follow.followed_id == owner_id,
    ).first() is not None


def can_view_audience(db: Session, *, owner_id: int, viewer_id: int, audience: str,
                      config: str | dict | None = None, blocked: bool = False,
                      restricted: bool = False) -> bool:
    if owner_id == viewer_id:
        return True
    cfg = normalize_audience_config(decode_config(config))
    included, excluded = set(cfg["included_ids"]), set(cfg["excluded_ids"])
    friends = are_friends(db, owner_id, viewer_id)
    follower = is_follower(db, viewer_id, owner_id)
    return post_is_visible(
        viewer_id=viewer_id, author_id=owner_id, privacy=audience,
        blocked=blocked, friends=friends, restricted=restricted,
        follower=follower, included=viewer_id in included,
        excluded=viewer_id in excluded, custom_base=cfg["base"],
    )


def privacy_settings(user) -> dict:
    stored = decode_config(user.privacy_settings)
    result = {}
    for field, default in PROFILE_DEFAULTS.items():
        item = stored.get(field, default)
        audience = item.get("audience", default["audience"]) if isinstance(item, dict) else default["audience"]
        if audience not in ADVANCED_AUDIENCES:
            audience = default["audience"]
        result[field] = {"audience": audience, **normalize_audience_config(item if isinstance(item, dict) else {})}
    return result


def encode_privacy_settings(value: dict) -> str:
    normalized = {}
    for field in PROFILE_FIELDS:
        item = value.get(field, {})
        audience = item.get("audience", PROFILE_DEFAULTS[field]["audience"])
        if audience not in ADVANCED_AUDIENCES:
            raise ValueError(f"Invalid audience for {field}")
        normalized[field] = {"audience": audience, **normalize_audience_config(item)}
    return json.dumps(normalized, separators=(",", ":"))


def can_view_profile_field(db: Session, owner, viewer_id: int, field: str) -> bool:
    setting = privacy_settings(owner)[field]
    return can_view_audience(db, owner_id=owner.id, viewer_id=viewer_id,
                             audience=setting["audience"], config=setting,
                             restricted=has_restricted(db, owner.id, viewer_id))
