from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse


OPTIONS_PATH = Path("/data/options.json")
DIRECT_PROXY_PORT = 18756
BACKEND_PORT = 18757
BACKEND_BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"

_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_DIRECT_PROXY_STRIPPED_PREFIXES = (
    "x-forwarded-",
    "x-hassio-",
    "x-ingress",
    "x-remote-user",
    "x-supervisor-",
)


def _load_options() -> dict[str, object]:
    try:
        if not OPTIONS_PATH.is_file():
            return {}
        raw = json.loads(OPTIONS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _setdefault_env(key: str, value: str) -> None:
    if os.getenv(key):
        return
    os.environ[key] = value


def _is_forwarded_header_allowed(header_name: str) -> bool:
    name = header_name.strip().lower()
    if name in _HOP_BY_HOP_HEADERS or name == "host":
        return False
    return not any(name.startswith(prefix) for prefix in _DIRECT_PROXY_STRIPPED_PREFIXES)


def _create_direct_proxy_app():
    from contextlib import asynccontextmanager

    import httpx
    from starlette.background import BackgroundTask

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.http = httpx.AsyncClient(timeout=None, follow_redirects=False)
        try:
            yield
        finally:
            await app.state.http.aclose()

    app = FastAPI(title="Toposync direct access proxy", lifespan=lifespan)

    @app.api_route(
        "/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    )
    async def proxy(request: Request, path: str) -> StreamingResponse:  # noqa: ARG001
        target = f"{BACKEND_BASE_URL}{request.url.path}"
        if request.url.query:
            target = f"{target}?{request.url.query}"

        headers = [
            (name, value)
            for name, value in request.headers.items()
            if _is_forwarded_header_allowed(name)
        ]
        outbound = request.app.state.http.build_request(
            request.method,
            target,
            headers=headers,
            content=request.stream(),
        )
        upstream = await request.app.state.http.send(outbound, stream=True)
        response = StreamingResponse(
            upstream.aiter_raw(),
            status_code=upstream.status_code,
            background=BackgroundTask(upstream.aclose),
        )
        response.raw_headers = [
            (name.encode("latin-1"), value.encode("latin-1"))
            for name, value in upstream.headers.multi_items()
            if _is_forwarded_header_allowed(name) and name.lower() != "content-length"
        ]
        return response

    return app


def _run_direct_proxy() -> None:
    import uvicorn

    uvicorn.run(
        _create_direct_proxy_app(),
        host="0.0.0.0",
        port=DIRECT_PROXY_PORT,
        log_level=str(os.getenv("TOPOSYNC_DIRECT_PROXY_LOG_LEVEL") or "warning"),
        access_log=False,
    )


def main() -> int:
    options = _load_options()
    log_level = str(options.get("log_level", "") or "").strip()
    if log_level:
        _setdefault_env("TOPOSYNC_LOG_LEVEL", log_level)

    _setdefault_env("TOPOSYNC_DATA_DIR", "/data")
    _setdefault_env("TOPOSYNC_STREAMING_ENGINE_CACHE_DIR", "/data/runtime")
    _setdefault_env("TOPOSYNC_AUTH_MODE", "home_assistant_hybrid")
    _setdefault_env("TOPOSYNC_AUTH_INGRESS_ROLE", "owner")
    _setdefault_env("TOPOSYNC_AUTH_INGRESS_TRUSTED_IPS", "127.0.0.1,::1,172.30.32.2,testclient")
    _setdefault_env("TOPOSYNC_AUTH_INGRESS_ENFORCE_TRUSTED", "1")
    _setdefault_env("TOPOSYNC_HOME_ASSISTANT_CONNECTION_MODE", "supervisor")

    threading.Thread(
        target=_run_direct_proxy,
        name="toposync-direct-proxy",
        daemon=True,
    ).start()

    proc = subprocess.run(
        [
            "toposync",
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            str(BACKEND_PORT),
            "--data-dir",
            "/data",
        ],
        check=False,
    )
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
