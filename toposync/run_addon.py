from __future__ import annotations

import asyncio
import ipaddress
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
STREAMING_WEBRTC_ICE_UDP_PORT = 18762
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

    if not isinstance(engine.get("expose_to_lan"), bool):
        engine["expose_to_lan"] = True
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


def _supervisor_network_info() -> dict[str, Any]:
    token = str(os.getenv("SUPERVISOR_TOKEN") or "").strip()
    if not token:
        return {}
    supervisor_url = str(os.getenv("SUPERVISOR") or "http://supervisor").strip().rstrip("/")
    if not supervisor_url:
        supervisor_url = "http://supervisor"

    import urllib.request

    request = urllib.request.Request(
        f"{supervisor_url}/network/info",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=2.0) as response:  # noqa: S310
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return payload["data"]
    return payload if isinstance(payload, dict) else {}


def _iter_network_addresses(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_iter_network_addresses(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for key in ("ip_address", "address", "addresses"):
            if key in value:
                out.extend(_iter_network_addresses(value.get(key)))
        ipv4 = value.get("ipv4")
        if isinstance(ipv4, dict):
            out.extend(_iter_network_addresses(ipv4))
        return out
    return []


def _normalize_lan_host(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        interface = ipaddress.ip_interface(text)
        ip = interface.ip
    except ValueError:
        try:
            ip = ipaddress.ip_address(text)
        except ValueError:
            return text
    if ip.version != 4:
        return ""
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
        return ""
    return str(ip)


def _resolve_addon_public_hosts() -> list[str]:
    hosts: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        host = _normalize_lan_host(raw)
        if not host:
            return
        key = host.lower()
        if key in seen:
            return
        seen.add(key)
        hosts.append(host)

    for item in str(os.getenv("TOPOSYNC_ADDON_PUBLIC_HOSTS") or "").replace(";", ",").split(","):
        add(item)

    try:
        info = _supervisor_network_info()
    except Exception as exc:  # noqa: BLE001
        print(f"Toposync add-on: could not read Supervisor network info for WebRTC hosts: {exc}", flush=True)
        info = {}

    interfaces_raw = info.get("interfaces") if isinstance(info, dict) else None
    if isinstance(interfaces_raw, dict):
        interfaces = list(interfaces_raw.values())
    elif isinstance(interfaces_raw, list):
        interfaces = interfaces_raw
    else:
        interfaces = []

    for item in interfaces:
        if not isinstance(item, dict):
            continue
        if item.get("enabled") is False or item.get("connected") is False:
            continue
        for address in _iter_network_addresses(item):
            add(address)

    add("homeassistant.local")
    return hosts


def _seed_streaming_env_defaults() -> None:
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_RTSP_PORT", str(STREAMING_RTSP_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_HLS_PORT", str(STREAMING_HLS_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_WEBRTC_PORT", str(STREAMING_WEBRTC_PORT))
    _setdefault_env("TOPOSYNC_STREAMING_PREFERRED_API_PORT", str(STREAMING_API_PORT))
    _setdefault_env(
        "TOPOSYNC_STREAMING_WEBRTC_LOCAL_UDP_ADDRESS",
        f":{STREAMING_WEBRTC_ICE_UDP_PORT}",
    )

    if not os.getenv("TOPOSYNC_STREAMING_WEBRTC_ADDITIONAL_HOSTS"):
        public_hosts = _resolve_addon_public_hosts()
        if public_hosts:
            os.environ["TOPOSYNC_STREAMING_WEBRTC_ADDITIONAL_HOSTS"] = ",".join(public_hosts)


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
        public_host = str(request.headers.get("host") or "").strip()
        if public_host:
            headers.append(("host", public_host))
            headers.append(("x-forwarded-host", public_host))
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
    _seed_streaming_env_defaults()

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
