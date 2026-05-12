from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.responses import FileResponse

from api.cast_manager import CastManager
from api.cast_routes import router as cast_router
from api.routes import router
from config import get_settings
from data.database import init_db


app = FastAPI(title="WatchThis", version="0.1.0")


@app.on_event("startup")
def startup():
    init_db()
    app.state.cast_manager = CastManager()

if get_settings().force_https:
    # Belt-and-suspenders: Railway's edge already redirects http→https, but if a
    # custom-domain misconfig or proxy regression ever lets plain HTTP reach the
    # app, this fails closed. Requires uvicorn --proxy-headers so the middleware
    # sees X-Forwarded-Proto from Railway's proxy.
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(cast_router)

# Serve built frontend in production
STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file = STATIC_DIR / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")
