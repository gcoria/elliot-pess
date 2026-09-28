"""Local chart server. The page only draws the JSON produced by the engine."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

_INDEX = Path(__file__).with_name("index.html")


def create_app(payload: dict) -> FastAPI:
    app = FastAPI()
    app.state.payload = payload

    @app.get("/")
    def index():
        return FileResponse(_INDEX)

    @app.get("/api/chart")
    def chart():
        return app.state.payload

    return app


def serve(payload: dict, host: str = "127.0.0.1", port: int = 8765, *, open_browser: bool = False) -> None:
    import threading
    import webbrowser

    import uvicorn

    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(create_app(payload), host=host, port=port, log_level="info")
