import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..config import settings
from ..models import User

router = APIRouter(prefix="/api/giphy", tags=["GIPHY"])


@router.get("")
def find_gifs(
    q: str = Query(default="", max_length=100),
    _: User = Depends(get_current_user),
):
    """Return a small, normalized GIPHY result set without exposing the API key."""
    if not settings.giphy_api_key:
        raise HTTPException(503, "GIPHY is not configured. Add GIPHY_API_KEY to .env.")

    query = q.strip()
    endpoint = "search" if query else "trending"
    params = {
        "api_key": settings.giphy_api_key,
        "limit": 24,
        "rating": "g",
        "bundle": "messaging_non_clips",
    }
    if query:
        params["q"] = query

    request = Request(
        f"https://api.giphy.com/v1/gifs/{endpoint}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "SocialN/1.0"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(502, "Could not load GIFs from GIPHY.") from exc

    results = []
    for item in payload.get("data", []):
        images = item.get("images") or {}
        preview = images.get("fixed_width_small") or images.get("fixed_width") or {}
        original = images.get("original") or preview
        preview_url = preview.get("webp") or preview.get("url")
        gif_url = original.get("webp") or original.get("url") or preview_url
        if not preview_url or not gif_url:
            continue
        results.append({
            "id": item.get("id"),
            "title": item.get("title") or "GIPHY GIF",
            "preview_url": preview_url,
            "url": gif_url,
            "width": int(original.get("width") or 0),
            "height": int(original.get("height") or 0),
        })
    return {"data": results}
