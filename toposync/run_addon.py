from __future__ import annotations

import asyncio
import json
import os
import subprocess
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from starlette.responses import StreamingResponse


OPTIONS_PATH = Path("/data/options.json")

# Keep the add-on in a project-owned port range instead of MediaMTX defaults.
DIRECT_PROXY_PORT = 18756
BACKEND_PORT = 18757
STREAMING_RTSP_PORT = 18758
STREAMING_HLS_PORT = 18759
STREAMING_WEBRTC_PORT = 18760
STREAMING_API_PORT = 18761
BACKEND_BASE_URL = f"http://127.0.0.1:{BACKEND_PORT}"
STREAMING_EXTENSION_ID = "com.toposync.streaming"
STREAMING_DEFAULT_PORTS = {
    "rtsp": STREAMING_RTSP_PORT,
    "hls": STREAMING_HLS_PORT,
    "webrtc": STREAMING_WEBRTC_PORT,
    "api": STREAMING_API_PORT,
}
STREAMING_LEGACY_DEFAULT_PORTS = {
    "rtsp": 8554,
    "hls": 8888,
    "webrtc": 8889,
    "api": 9997,
}

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
    except Exception:  # noqa: BLE001
        return {}
    return raw if isinstance(raw, dict) else {}


def _setdefault_env(key: str, value: str) -> None:
    if os.getenv(key):
        return
    os.environ[key] = value


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value or "").strip())
    except Exception:  # noqa: BLE001
        return None


def _merge_streaming_addon_defaults(raw: Any) -> tuple[dict[str, Any], bool]:
    settings = deepcopy(raw) if isinstance(raw, dict) else {}
    changed = not isinstance(raw, dict)

    engine = settings.get("engine")
    if not isinstance(engine, dict):
        engine = {}
        settings["engine"] = engine
        changed = True

    preferred_ports = engine.get("preferred_ports")
    if not isinstance(preferred_ports, dict):
        preferred_ports = {}
        engine["preferred_ports"] = preferred_ports
        changed = True

    for key, target_port in STREAMING_DEFAULT_PORTS.items():
        current_port = _as_int(preferred_ports.get(key))
        legacy_port = STREAMING_LEGACY_DEFAULT_PORTS.get(key)
        if current_port is None or current_port == legacy_port:
            if current_port != target_port:
                preferred_ports[key] = target_port
                changed = True

    return settings, changed


async def _seed_toposync_config_defaults() -> None:
    try:
        from toposync.runtime.config_store import AppSettings, ConfigStore, UserDataPaths
    except Exception as exc:  # noqa: BLE001
        print(f"Toposync add-on: skipping startup config defaults: {exc}", flush=True)
        return

    try:
        paths = UserDataPaths.resolve()
    except Exception:  # noqa: BLE001
        paths = UserDataPaths(
            data_dir=Path("/data"),
            config_path=Path("/data/config.json"),
            files_dir=Path("/data/files"),
        )
    config_store = ConfigStore(paths=paths)
    settings = await config_store.get_settings()
    core = dict(settings.core) if isinstance(settings.core, dict) else {}
    extensions = dict(settings.extensions) if isinstance(settings.extensions, dict) else {}

    streaming, streaming_changed = _merge_streaming_addon_defaults(
        extensions.get(STREAMING_EXTENSION_ID)
    )
    if streaming_changed:
        extensions[STREAMING_EXTENSION_ID] = streaming
        await config_store.replace_settings(AppSettings(core=core, extensions=extensions))


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
    _setdefault_env(
        "TOPOSYNC_AUTH_INGRESS_TRUSTED_IPS",
        "127.0.0.1,::1,172.30.32.2,testclient",
    )
    _setdefault_env("TOPOSYNC_AUTH_INGRESS_ENFORCE_TRUSTED", "1")
    _setdefault_env("TOPOSYNC_HOME_ASSISTANT_CONNECTION_MODE", "supervisor")
    _setdefault_env("TOPOSYNC_EXTENSION_AUTO_INSTALL_ON_STARTUP", "1")
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_RTSP_PORT", str(STREAMING_RTSP_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_HLS_PORT", str(STREAMING_HLS_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_WEBRTC_PORT", str(STREAMING_WEBRTC_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_API_PORT", str(STREAMING_API_PORT))

    asyncio.run(_seed_toposync_config_defaults())

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
