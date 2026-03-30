from __future__ import annotations

import socket
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(prefix="/cast", tags=["cast"])

# In-memory store for cast payloads (cast_id -> recommendation data)
# Chromecast loads the URL, we serve the data from here
_cast_store: dict[str, dict[str, Any]] = {}


class StreamingSourceInput(BaseModel):
    name: str
    type: str = "sub"
    web_url: str | None = None


class RecommendationInput(BaseModel):
    title: str
    year: int | None = None
    media_type: str | None = None
    runtime: int | None = None
    poster_url: str | None = None
    genres: list[str] = []
    pitch: str = ""
    confidence: float | None = None
    vote_average: float | None = None
    rt_score: str | None = None
    metacritic: int | None = None
    imdb_rating: float | None = None
    streaming_sources: list[StreamingSourceInput] = []


class CastShowInput(BaseModel):
    recommendation: RecommendationInput
    device_name: str | None = None


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


@router.get("/status")
async def cast_status(request: Request):
    cm = request.app.state.cast_manager
    saved = cm.get_saved_device()
    return {"configured": saved is not None, "device_name": saved}


@router.get("/devices")
async def cast_devices(request: Request):
    cm = request.app.state.cast_manager
    devices = await cm.scan_devices()
    return {"devices": devices}


@router.post("/show")
async def cast_show(payload: CastShowInput, request: Request):
    cm = request.app.state.cast_manager

    # Determine device
    device = payload.device_name or cm.get_saved_device()
    if not device:
        # Auto-scan and pick if only one device
        devices = await cm.scan_devices()
        if not devices:
            raise HTTPException(
                status_code=404,
                detail="No Chromecast devices found on your network. Is your TV on?",
            )
        if len(devices) == 1:
            device = devices[0]["name"]
            cm.save_device(device)
        else:
            return {
                "sent": False,
                "needs_selection": True,
                "devices": devices,
            }

    # Save device for future use
    if not cm.get_saved_device():
        cm.save_device(device)

    # Store recommendation data for the cast view
    cast_id = uuid.uuid4().hex[:12]
    _cast_store[cast_id] = payload.recommendation.model_dump()

    # Keep store from growing unbounded
    if len(_cast_store) > 50:
        oldest = list(_cast_store.keys())[:-50]
        for k in oldest:
            _cast_store.pop(k, None)

    # Build the URL the Chromecast will render
    local_ip = _get_local_ip()
    view_url = f"http://{local_ip}:8000/cast/view/{cast_id}"

    success = await cm.cast_url(view_url, device)
    if not success:
        raise HTTPException(status_code=502, detail="Couldn't reach your TV. Is it on?")

    return {"sent": True, "device": device}


@router.post("/stop")
async def cast_stop(request: Request):
    cm = request.app.state.cast_manager
    device = cm.get_saved_device()
    if not device:
        return {"stopped": False, "detail": "No device configured"}
    try:
        await cm.stop_cast(device)
        return {"stopped": True, "device": device}
    except Exception as e:
        return {"stopped": False, "detail": str(e)}


@router.get("/view/{cast_id}", response_class=HTMLResponse)
async def cast_view(cast_id: str):
    """Server-rendered recommendation page for Chromecast DashCast."""
    data = _cast_store.get(cast_id)
    if not data:
        return HTMLResponse(
            "<html><body style='background:#0a0a0a;color:#fff;display:flex;align-items:center;"
            "justify-content:center;height:100vh;font-family:system-ui'>"
            "<h1>Session expired</h1></body></html>",
            status_code=404,
        )

    title = data.get("title", "Unknown")
    year = data.get("year", "")
    media_type = (data.get("media_type") or "").upper()
    runtime = data.get("runtime")
    pitch = data.get("pitch", "")
    confidence = data.get("confidence")
    poster_url = data.get("poster_url") or ""
    genres = data.get("genres", [])
    vote_average = data.get("vote_average")
    rt_score = data.get("rt_score")
    metacritic = data.get("metacritic")
    imdb_rating = data.get("imdb_rating")
    streaming_sources = data.get("streaming_sources", [])

    # Build meta line
    meta_parts = [p for p in [media_type, str(year) if year else None, f"{runtime}m" if runtime else None] if p]
    meta_line = " &bull; ".join(meta_parts)

    # Genres
    genres_html = ""
    if genres:
        pills = "".join(f'<span class="genre">{g}</span>' for g in genres[:4])
        genres_html = f'<div class="genres">{pills}</div>'

    # Poster
    poster_html = ""
    if poster_url:
        poster_html = f'<img src="{poster_url}" class="poster" alt="{title}" onerror="this.parentElement.style.display=\'none\'" />'

    # Confidence badge
    conf_html = ""
    if confidence and confidence > 0:
        pct = int(float(confidence) * 100)
        conf_html = f'<div class="confidence">{pct}% match</div>'

    # Ratings
    ratings = []
    if vote_average and vote_average > 0:
        ratings.append(("TMDB", f"{vote_average:.1f}", "tmdb"))
    if rt_score:
        ratings.append(("RT", rt_score, "rt"))
    if metacritic and metacritic > 0:
        ratings.append(("Metacritic", str(metacritic), "mc"))
    if imdb_rating and imdb_rating > 0:
        ratings.append(("IMDb", f"{imdb_rating:.1f}", "imdb"))

    ratings_html = ""
    if ratings:
        items = "".join(
            f'<div class="rating"><div class="rating-value rating-{cls}">{val}</div>'
            f'<div class="rating-label">{label}</div></div>'
            for label, val, cls in ratings
        )
        ratings_html = f'<div class="ratings">{items}</div>'

    # Streaming sources
    streaming_html = ""
    if streaming_sources:
        pills = "".join(
            f'<span class="stream-pill stream-{s.get("type", "sub")}">{s["name"]}</span>'
            for s in streaming_sources[:6]
        )
        streaming_html = f'<div class="streaming"><div class="streaming-label">Where to watch</div><div class="stream-row">{pills}</div></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title} — WatchThis</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: #0a0a0a;
    color: #f0f0f0;
    font-family: 'Inter', -apple-system, system-ui, sans-serif;
    height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}

  .container {{
    display: flex;
    gap: 56px;
    max-width: 1280px;
    width: 100%;
    padding: 40px 56px;
    align-items: center;
    animation: fadeIn 0.8s ease-out;
  }}

  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(24px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  @keyframes slideUp {{
    from {{ opacity: 0; transform: translateY(32px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .poster-wrap {{
    flex-shrink: 0;
    animation: slideUp 0.8s ease-out 0.15s both;
  }}

  .poster {{
    width: 300px;
    border-radius: 14px;
    box-shadow:
      0 20px 60px rgba(0,0,0,0.5),
      0 0 80px rgba(47, 127, 122, 0.1);
  }}

  .info {{
    flex: 1;
    min-width: 0;
    animation: slideUp 0.8s ease-out 0.3s both;
  }}

  .title {{
    font-size: 52px;
    font-weight: 800;
    line-height: 1.08;
    letter-spacing: -0.025em;
    margin-bottom: 8px;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }}

  .meta {{
    font-size: 17px;
    color: #9ca3af;
    font-weight: 500;
    margin-bottom: 16px;
  }}

  .genres {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 20px;
  }}

  .genre {{
    padding: 4px 14px;
    background: rgba(255,255,255,0.06);
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
    color: #d1d5db;
  }}

  .confidence {{
    display: inline-block;
    padding: 5px 14px;
    background: rgba(47, 127, 122, 0.15);
    border: 1px solid rgba(47, 127, 122, 0.35);
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    color: #5BAE8A;
    margin-bottom: 20px;
  }}

  .pitch {{
    font-size: 22px;
    line-height: 1.5;
    color: #d1d5db;
    margin-bottom: 32px;
    max-width: 540px;
  }}

  .ratings {{
    display: flex;
    gap: 28px;
    margin-bottom: 28px;
  }}

  .rating {{ text-align: center; }}

  .rating-value {{
    font-size: 26px;
    font-weight: 700;
  }}

  .rating-label {{
    font-size: 11px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 3px;
  }}

  .rating-tmdb {{ color: #01b4e4; }}
  .rating-rt {{ color: #fa320a; }}
  .rating-mc {{ color: #66cc33; }}
  .rating-imdb {{ color: #f5c518; }}

  .streaming {{ margin-top: 4px; }}

  .streaming-label {{
    font-size: 13px;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 10px;
  }}

  .stream-row {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
  }}

  .stream-pill {{
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 500;
    background: rgba(255,255,255,0.08);
    color: #e5e7eb;
  }}

  .stream-sub {{ border: 1px solid rgba(47, 127, 122, 0.3); color: #5BAE8A; }}
  .stream-rent {{ border: 1px solid rgba(217, 164, 65, 0.3); color: #D9A441; }}
  .stream-buy {{ border: 1px solid rgba(232, 110, 110, 0.3); color: #E86E6E; }}
  .stream-free {{ border: 1px solid rgba(91, 174, 138, 0.3); color: #5BAE8A; }}

  .branding {{
    position: fixed;
    bottom: 20px;
    right: 28px;
    font-size: 13px;
    color: #374151;
    font-weight: 600;
    letter-spacing: 0.06em;
  }}
</style>
</head>
<body>
  <div class="container">
    <div class="poster-wrap">
      {poster_html}
    </div>
    <div class="info">
      <h1 class="title">{title}</h1>
      <p class="meta">{meta_line}</p>
      {genres_html}
      {conf_html}
      <p class="pitch">{pitch}</p>
      {ratings_html}
      {streaming_html}
    </div>
  </div>
  <div class="branding">WatchThis</div>
</body>
</html>"""
    return HTMLResponse(html)
