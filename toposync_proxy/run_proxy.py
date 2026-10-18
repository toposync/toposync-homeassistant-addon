"""Validate add-on options and start the ingress-only reverse proxy."""

from __future__ import annotations

import ipaddress
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit


TOKEN_PATTERN = r"[A-Za-z0-9_-]{32,256}"


def render_config(options: dict, resolvers: list[str]) -> str:
    if not isinstance(options, dict):
        raise ValueError("Add-on options must be an object")
    server_url = options.get("server_url", "")
    token = options.get("proxy_token", "")
    allow_http = options.get("allow_http", False)
    if (
        not isinstance(server_url, str)
        or not server_url.isascii()
        or re.search(r"\s|[\\?#]", server_url)
    ):
        raise ValueError(
            "server_url must be an HTTP(S) origin without credentials, path or query"
        )
    try:
        server = urlsplit(server_url)
        hostname = server.hostname or ""
        port = (
            server.port
            if server.port is not None
            else (443 if server.scheme == "https" else 80)
        )
    except ValueError:
        raise ValueError("server_url contains an invalid host or port") from None
    if (
        server.scheme not in {"http", "https"}
        or not hostname
        or server.username is not None
        or server.password is not None
        or server.path not in {"", "/"}
        or not 1 <= port <= 65535
        or server.netloc.endswith(":")
    ):
        raise ValueError(
            "server_url must be an HTTP(S) origin without credentials, path or query"
        )
    try:
        address = ipaddress.ip_address(hostname)
        if "%" in hostname:
            raise ValueError("Scoped addresses are not supported")
        host = f"[{address}]" if address.version == 6 else str(address)
    except ValueError:
        label = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
        if len(hostname) > 253 or not re.fullmatch(rf"{label}(?:\.{label})*", hostname):
            raise ValueError("server_url contains an invalid host") from None
        host = hostname
    if type(allow_http) is not bool:
        raise ValueError("allow_http must be a boolean")
    if server.scheme == "http" and not allow_http:
        raise ValueError(
            "Use HTTPS, or enable allow_http only over an encrypted private tunnel"
        )
    if not isinstance(token, str) or not re.fullmatch(TOKEN_PATTERN, token):
        raise ValueError("proxy_token must contain 32–256 URL-safe characters")
    nameservers = []
    for resolver in resolvers:
        if "%" in resolver:
            raise ValueError("Scoped DNS resolver addresses are not supported")
        try:
            address = ipaddress.ip_address(resolver)
        except ValueError:
            raise ValueError("Invalid DNS nameserver address") from None
        nameservers.append(f"[{address}]" if address.version == 6 else str(address))
    if not nameservers:
        raise ValueError("No DNS nameserver is configured")
    headers = f'''proxy_set_header Host $proxy_host;
            proxy_set_header X-Forwarded-Host $http_host;
            proxy_set_header X-Forwarded-Proto $public_scheme;
            proxy_set_header X-Forwarded-For "";
            proxy_set_header X-Real-IP "";
            proxy_set_header Forwarded "";
            proxy_set_header X-Forwarded-Prefix "";
            proxy_set_header X-Script-Name "";
            proxy_set_header X-Ingress-Path $http_x_ingress_path;
            proxy_set_header X-Remote-User-Id $http_x_remote_user_id;
            proxy_set_header X-Remote-User-Name $http_x_remote_user_name;
            proxy_set_header X-Remote-User-Display-Name $http_x_remote_user_display_name;
            proxy_set_header X-Toposync-Ingress-Token "{token}";
            proxy_set_header Authorization "";
            proxy_set_header Cookie "toposync_at=$cookie_toposync_at; toposync_rt=$cookie_toposync_rt";'''
    template = (
        Path(__file__).with_name("nginx.conf.template").read_text(encoding="utf-8")
    )
    for placeholder, value in {
        "__ORIGIN__": f"{server.scheme}://{host}:{port}",
        "__TLS_NAME__": hostname,
        "__REDIRECT_AUTHORITY__": re.escape(host)
        + (
            f"(?::{port})?"
            if port == (443 if server.scheme == "https" else 80)
            else f":{port}"
        ),
        "__RESOLVERS__": " ".join(nameservers),
        "__HEADERS__": headers,
    }.items():
        template = template.replace(placeholder, value)
    return template


def main() -> None:
    try:
        options = json.loads(Path("/data/options.json").read_text(encoding="utf-8"))
        resolvers = []
        for line in Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                resolvers.append(parts[1])
        config = render_config(options, resolvers)
        runtime = Path("/run/nginx")
        runtime.mkdir(parents=True, exist_ok=True)
        config_path = runtime / "toposync.conf"
        descriptor = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as writer:
            os.fchmod(writer.fileno(), 0o600)
            writer.write(config)
    except (OSError, json.JSONDecodeError, UnicodeError):
        print(
            "Toposync Remote Instance: cannot read options or write runtime configuration. "
            "Check the saved configuration and add-on storage.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except ValueError as error:
        # Validation messages are fixed text and never include option values.
        print(
            f"Toposync Remote Instance: {error}. Open Configuration, correct the field and restart.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    os.execvp("nginx", ["nginx", "-c", str(config_path)])


if __name__ == "__main__":
    main()
