from __future__ import annotations

import base64
import hashlib
from http import client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import io
from contextlib import redirect_stderr
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_proxy", ROOT / "toposync_proxy/run_proxy.py"
)
proxy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(proxy)
TOKEN = "test-proxy-token-" + "a" * 32
OPTIONS = {"server_url": "https://toposync.example.test", "proxy_token": TOKEN}
HEADERS = {
    "X-Ingress-Path": "/api/hassio_ingress/test123",
    "X-Remote-User-Id": "first-user",
    "Host": "ha.example.test",
}
NGINX = os.getenv("NGINX_BINARY") or shutil.which("nginx")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class ProxyOptionsTest(unittest.TestCase):
    def test_rejects_unsafe_options_without_echoing_credentials(self):
        invalid_urls = [
            "ftp://host",
            "https://user:password@host",
            "https://host/path",
            "https://host?",
            "https://host#",
            "https://host:0",
            "https://host:65536",
            "https://host:",
            "https://bad;host",
            "https://host\ninclude /secret;",
            "https://host\\evil",
            "http://host",
        ]
        for url in invalid_urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                proxy.render_config({**OPTIONS, "server_url": url}, ["127.0.0.11"])
        for token in ["", "short", "a" * 32 + '";', "a" * 257, 123]:
            with self.subTest(token=token), self.assertRaises(ValueError) as error:
                proxy.render_config({**OPTIONS, "proxy_token": token}, ["127.0.0.11"])
            if token:
                self.assertNotIn(str(token), str(error.exception))
        with self.assertRaises(ValueError):
            proxy.render_config(OPTIONS, ["bad;resolver"])
        with self.assertRaises(ValueError):
            proxy.render_config({**OPTIONS, "allow_http": "true"}, ["127.0.0.11"])

    def test_startup_reports_the_invalid_field_without_credentials(self):
        for options, field in [
            (
                {**OPTIONS, "server_url": "https://secret-user:secret-password@host"},
                "server_url",
            ),
            ({**OPTIONS, "proxy_token": "invalid-secret"}, "proxy_token"),
            ({**OPTIONS, "server_url": "http://host"}, "allow_http"),
            ([], "options"),
        ]:
            output = io.StringIO()
            with (
                self.subTest(field=field),
                mock.patch.object(
                    Path,
                    "read_text",
                    side_effect=[json.dumps(options), "nameserver 127.0.0.11"],
                ),
                mock.patch.object(os, "execvp") as execute,
                redirect_stderr(output),
                self.assertRaises(SystemExit) as error,
            ):
                proxy.main()
            self.assertEqual(error.exception.code, 1)
            self.assertIn(field, output.getvalue())
            for secret in [TOKEN, "invalid-secret", "secret-user", "secret-password"]:
                self.assertNotIn(secret, output.getvalue())
            execute.assert_not_called()

    def test_unreadable_or_malformed_options_fail_without_echoing_input(self):
        for value in ["malformed-secret", OSError("sensitive-path")]:
            output = io.StringIO()
            with (
                self.subTest(value=value),
                mock.patch.object(Path, "read_text", side_effect=[value]),
                redirect_stderr(output),
                self.assertRaises(SystemExit),
            ):
                proxy.main()
            self.assertIn("cannot read options", output.getvalue())
            self.assertNotIn(str(value), output.getvalue())

    def test_https_ipv6_and_explicit_tunnel_options(self):
        for url in [
            "https://toposync.example.test",
            "https://[::1]:8000/",
            "https://192.0.2.10",
        ]:
            config = proxy.render_config(
                {**OPTIONS, "server_url": url}, ["127.0.0.11", "::1"]
            )
            self.assertIn("proxy_ssl_verify on;", config)
            self.assertNotIn("__ORIGIN__", config)
        config = proxy.render_config(
            {**OPTIONS, "server_url": "http://127.0.0.1:8000", "allow_http": True},
            ["127.0.0.11"],
        )
        self.assertIn('set $upstream_origin "http://127.0.0.1:8000";', config)


class Resolver:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.settimeout(0.1)
        self.port = self.socket.getsockname()[1]
        self.available = True
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                query, sender = self.socket.recvfrom(4096)
            except socket.timeout:
                continue
            end = 12
            while query[end]:
                end += query[end] + 1
            question = query[12 : end + 5]
            answer = (
                b"\xc0\x0c"
                + struct.pack("!HHIH", 1, 1, 1, 4)
                + socket.inet_aton("127.0.0.1")
            )
            response = (
                query[:2]
                + struct.pack(
                    "!HHHHH",
                    0x8180 if self.available else 0x8183,
                    1,
                    int(self.available),
                    0,
                    0,
                )
                + question
            )
            self.socket.sendto(response + (answer if self.available else b""), sender)

    def close(self):
        self.stopped.set()
        self.thread.join(timeout=2)
        self.socket.close()


class Upstream(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    auth_status = 204
    expected_host = None
    received = []
    continue_stream = threading.Event()

    def log_message(self, *_args):
        pass

    def respond(self, status, body=b"", headers=None):
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.expected_host and self.headers.get("Host") != self.expected_host:
            self.respond(421)
            return
        if self.path == "/api/auth/ingress-proxy":
            valid = self.headers.get(
                "X-Toposync-Ingress-Token"
            ) == TOKEN and self.headers.get("X-Remote-User-Id")
            self.respond(type(self).auth_status if valid else 403)
        elif self.path == "/events":
            first = b"data: first\n\n"
            second = b"data: second\n\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(first) + len(second)))
            self.end_headers()
            self.wfile.write(first)
            self.wfile.flush()
            type(self).continue_stream.wait(4)
            self.wfile.write(second)
        elif self.path == "/ws":
            key = (
                self.headers["Sec-WebSocket-Key"]
                + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            )
            self.send_response(101)
            self.send_header("Upgrade", "websocket")
            self.send_header("Connection", "Upgrade")
            self.send_header(
                "Sec-WebSocket-Accept",
                base64.b64encode(hashlib.sha1(key.encode()).digest()).decode(),
            )
            self.end_headers()
            self.rfile.read(8)
            self.wfile.write(b"\x81\x02ok")
            self.wfile.flush()
        elif self.path == "/range":
            self.respond(206, b"2345", {"Content-Range": "bytes 2-5/10"})
        elif self.path.startswith("/redirect"):
            target = self.path.partition("?target=")[2]
            self.respond(
                307,
                headers={
                    "Location": target,
                    "Set-Cookie": "toposync_at=local; Path=/; HttpOnly",
                },
            )
        elif self.path == "/forbidden":
            self.respond(
                403, b'{"detail":"not allowed"}', {"Content-Type": "application/json"}
            )
        else:
            self.respond(
                200,
                json.dumps({"path": self.path, "headers": dict(self.headers)}).encode(),
            )

    def do_POST(self):
        if self.headers.get("Transfer-Encoding") == "chunked":
            body = b""
            while True:
                size = int(self.rfile.readline().strip(), 16)
                if not size:
                    self.rfile.readline()
                    break
                body += self.rfile.read(size)
                self.rfile.read(2)
        else:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        type(self).received.append(body)
        self.respond(
            201,
            body,
            {
                "Content-Type": "application/octet-stream",
                "Content-Disposition": 'attachment; filename="image.bin"',
            },
        )


@unittest.skipUnless(NGINX, "Set NGINX_BINARY to run real proxy integration tests")
class ProxyIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.runtime = Path(cls.directory.name)
        (cls.runtime / "logs").mkdir()
        cls.upstream = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
        cls.thread = threading.Thread(target=cls.upstream.serve_forever, daemon=True)
        cls.thread.start()
        cls.resolver = Resolver()
        cls.port = free_port()
        cls.health_port = free_port()
        cls.start_proxy()

    @classmethod
    def start_proxy(cls, *, origin=None, allow_source=True, certificate=None):
        config = proxy.render_config(
            {
                **OPTIONS,
                "server_url": origin or f"http://127.0.0.1:{cls.upstream.server_port}",
                "allow_http": True,
            },
            ["127.0.0.1"],
        )
        config = config.replace(
            "resolver 127.0.0.1 valid=30s;",
            f"resolver 127.0.0.1:{cls.resolver.port} valid=1s ipv6=off;",
        )
        config = config.replace("/run/nginx", str(cls.runtime)).replace(
            "user nginx;", ""
        )
        config = config.replace("listen 8099;", f"listen 127.0.0.1:{cls.port};")
        config = config.replace(
            "listen 127.0.0.1:8098;", f"listen 127.0.0.1:{cls.health_port};"
        )
        if allow_source:
            config = config.replace("allow 172.30.32.2;", "allow 127.0.0.1;")
        config = config.replace(
            "/etc/ssl/certs/ca-certificates.crt",
            str(certificate or ssl.get_default_verify_paths().cafile),
        )
        cls.config_path = cls.runtime / "nginx.conf"
        cls.config_path.write_text(config)
        cls.process = subprocess.Popen(
            [NGINX, "-p", str(cls.runtime), "-c", str(cls.config_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        for _ in range(100):
            if cls.process.poll() is not None:
                raise AssertionError(cls.process.stderr.read().decode())
            try:
                with socket.create_connection(("127.0.0.1", cls.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.02)
        raise AssertionError("Nginx did not start")

    @classmethod
    def stop_proxy(cls):
        cls.process.terminate()
        cls.process.communicate(timeout=5)

    @classmethod
    def tearDownClass(cls):
        cls.stop_proxy()
        cls.upstream.shutdown()
        cls.upstream.server_close()
        cls.resolver.close()
        cls.directory.cleanup()

    def request(self, path="/", *, method="GET", body=None, headers=None):
        connection = client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        connection.request(
            method, path, body=body, headers=HEADERS if headers is None else headers
        )
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_preserves_request_identity_paths_queries_and_filters_secrets(self):
        for user in ["first-user", "second-user"]:
            status, _, body = self.request(
                "/extensions/example/image%20file.jpg?media_token=signed%2Bvalue",
                headers={
                    **HEADERS,
                    "X-Remote-User-Id": user,
                    "X-Toposync-Ingress-Token": "forged",
                    "X-Forwarded-For": "172.30.32.2",
                    "Authorization": "Bearer ha-secret",
                    "Cookie": "ingress_session=ha-secret; toposync_at=local",
                },
            )
            self.assertEqual(status, 200)
            payload = json.loads(body)
            self.assertEqual(
                payload["path"],
                "/extensions/example/image%20file.jpg?media_token=signed%2Bvalue",
            )
            forwarded = {
                key.lower(): value for key, value in payload["headers"].items()
            }
            self.assertEqual(forwarded["x-remote-user-id"], user)
            self.assertEqual(forwarded["x-toposync-ingress-token"], TOKEN)
            self.assertNotIn("x-forwarded-for", forwarded)
            self.assertNotIn("authorization", forwarded)
            self.assertNotIn("ha-secret", forwarded["cookie"])

    def test_virtual_host_uses_remote_address_and_preserves_public_host(self):
        Upstream.expected_host = f"127.0.0.1:{self.upstream.server_port}"
        try:
            status, _, body = self.request()
            self.assertEqual(status, 200)
            headers = json.loads(body)["headers"]
            self.assertEqual(headers["Host"], Upstream.expected_host)
            self.assertEqual(headers["X-Forwarded-Host"], HEADERS["Host"])
        finally:
            Upstream.expected_host = None

    def test_connection_and_authentication_errors_follow_browser_language(self):
        for status, phrase in [(403, "acesso negado"), (404, "conexão indisponível")]:
            Upstream.auth_status = status
            try:
                for language in ["pt-BR,pt;q=0.9,en;q=0.8", "pt-PT", "pt"]:
                    response, headers, body = self.request(
                        headers={**HEADERS, "Accept-Language": language}
                    )
                    self.assertEqual(response, 403 if status == 403 else 502)
                    self.assertEqual(headers["Content-Language"], "pt-BR")
                    self.assertIn("charset=utf-8", headers["Content-Type"])
                    self.assertIn(phrase, body.decode())
                    self.assertIn("no-store", headers["Cache-Control"])
                    self.assertNotIn(TOKEN.encode(), body)
                for language in ["en-US,pt;q=0.8", "fr", ""]:
                    _, headers, body = self.request(
                        headers={**HEADERS, "Accept-Language": language}
                    )
                    self.assertEqual(headers["Content-Language"], "en")
                    self.assertIn(b"Remote Instance", body)
            finally:
                Upstream.auth_status = 204

    def test_rejects_missing_identity_path_and_backend_contract(self):
        for headers in [
            {},
            {"X-Ingress-Path": HEADERS["X-Ingress-Path"]},
            {"X-Remote-User-Id": "owner"},
        ]:
            self.assertEqual(self.request(headers=headers)[0], 403)
        for backend_status, expected in [(403, 403), (404, 502), (500, 502)]:
            Upstream.auth_status = backend_status
            try:
                self.assertEqual(self.request()[0], expected)
            finally:
                Upstream.auth_status = 204
        self.assertEqual(self.request("/_toposync_proxy_auth")[0], 404)

    def test_upload_download_range_and_api_errors(self):
        body = b"image-data" * 110000
        status, headers, received = self.request("/files", method="POST", body=body)
        self.assertEqual(status, 201)
        self.assertEqual(received, body)
        self.assertEqual(Upstream.received[-1], body)
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertEqual(
            self.request("/files", method="POST", body=iter([b"first", b"second"]))[2],
            b"firstsecond",
        )
        status, headers, body = self.request(
            "/range", headers={**HEADERS, "Range": "bytes=2-5"}
        )
        self.assertEqual(
            (status, body, headers["Content-Range"]), (206, b"2345", "bytes 2-5/10")
        )
        self.assertEqual(self.request("/forbidden")[2], b'{"detail":"not allowed"}')

    def test_redirects_and_cookie_paths_keep_ingress_prefix_once(self):
        prefix = HEADERS["X-Ingress-Path"]
        for target in [
            "/settings/",
            f"{prefix}/settings/",
            "http://ha.example.test/settings/",
            f"http://127.0.0.1:{self.upstream.server_port}/settings/",
            f"https://127.0.0.1:{self.upstream.server_port}/settings/",
        ]:
            status, headers, _ = self.request("/redirect?target=" + target)
            self.assertEqual(status, 307)
            self.assertEqual(headers["Location"], prefix + "/settings/")
            self.assertIn("Path=" + prefix + "/", headers["Set-Cookie"])

        for target in [
            "https://external.example.test/settings/",
            f"https://127x0x0x1:{self.upstream.server_port}/settings/",
        ]:
            _, headers, _ = self.request("/redirect?target=" + target)
            self.assertEqual(headers["Location"], target)

    def test_events_are_forwarded_before_stream_finishes(self):
        Upstream.continue_stream.clear()
        connection = client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request("GET", "/events", headers=HEADERS)
            response = connection.getresponse()
            self.assertEqual(response.read(13), b"data: first\n\n")
            Upstream.continue_stream.set()
            self.assertEqual(response.read(), b"data: second\n\n")
        finally:
            Upstream.continue_stream.set()
            connection.close()

    def test_websocket_upgrade_and_bidirectional_bytes(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=3) as sock:
            headers = {
                **HEADERS,
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Key": base64.b64encode(b"0123456789abcdef").decode(),
                "Sec-WebSocket-Version": "13",
            }
            sock.sendall(
                (
                    "GET /ws HTTP/1.1\r\n"
                    + "".join(f"{k}: {v}\r\n" for k, v in headers.items())
                    + "\r\n"
                ).encode()
            )
            stream = sock.makefile("rb")
            self.assertIn(b"101", stream.readline())
            while stream.readline() != b"\r\n":
                pass
            sock.sendall(b"\x81\x82\x00\x00\x00\x00hi")
            self.assertEqual(stream.read(4), b"\x81\x02ok")
            stream.close()

    def test_source_restriction_and_unavailable_recovery(self):
        self.stop_proxy()
        recovering_server = None
        try:
            self.start_proxy(allow_source=False)
            self.assertEqual(self.request()[0], 403)
            self.stop_proxy()
            port = free_port()
            self.start_proxy(origin=f"http://127.0.0.1:{port}")
            self.assertEqual(self.request()[0], 502)
            health = client.HTTPConnection("127.0.0.1", self.health_port, timeout=2)
            health.request("GET", "/")
            self.assertEqual(health.getresponse().status, 200)
            health.close()
            recovering_server = ThreadingHTTPServer(("127.0.0.1", port), Upstream)
            threading.Thread(
                target=recovering_server.serve_forever, daemon=True
            ).start()
            self.assertEqual(self.request()[0], 200)
        finally:
            self.stop_proxy()
            if recovering_server:
                recovering_server.shutdown()
                recovering_server.server_close()
            self.start_proxy()

    def test_dns_recovers_without_restarting_proxy(self):
        self.stop_proxy()
        try:
            self.resolver.available = False
            self.start_proxy(origin=f"http://toposync.test:{self.upstream.server_port}")
            self.assertEqual(self.request()[0], 502)
            self.resolver.available = True
            deadline = time.monotonic() + 4
            while self.request()[0] != 200:
                if time.monotonic() >= deadline:
                    self.fail("DNS did not recover without restarting Nginx")
                time.sleep(0.1)
        finally:
            self.resolver.available = True
            self.stop_proxy()
            self.start_proxy()

    @unittest.skipUnless(
        shutil.which("openssl"), "OpenSSL is needed for HTTPS integration tests"
    )
    def test_https_requires_trusted_certificate_and_matching_name(self):
        self.stop_proxy()
        try:
            for name, address in [
                ("matching", "toposync.test"),
                ("wrong-name", "other.test"),
            ]:
                cert = self.runtime / f"{name}.crt"
                key = self.runtime / f"{name}.key"
                config = self.runtime / f"{name}.cnf"
                config.write_text(
                    f"[req]\ndistinguished_name=dn\nx509_extensions=v3\nprompt=no\n[dn]\nCN=toposync-test\n[v3]\nsubjectAltName=DNS:{address}\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,digitalSignature,keyEncipherment,keyCertSign\n"
                )
                subprocess.run(
                    [
                        "openssl",
                        "req",
                        "-x509",
                        "-newkey",
                        "rsa:2048",
                        "-nodes",
                        "-days",
                        "1",
                        "-config",
                        str(config),
                        "-keyout",
                        str(key),
                        "-out",
                        str(cert),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(cert, key)
                server.socket = context.wrap_socket(server.socket, server_side=True)
                threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    origin = f"https://toposync.test:{server.server_port}"
                    self.start_proxy(origin=origin)
                    self.assertEqual(self.request()[0], 502)
                    self.stop_proxy()
                    Upstream.expected_host = f"toposync.test:{server.server_port}"
                    self.start_proxy(origin=origin, certificate=cert)
                    self.assertEqual(
                        self.request()[0], 200 if name == "matching" else 502
                    )
                    self.stop_proxy()
                finally:
                    Upstream.expected_host = None
                    server.shutdown()
                    server.server_close()
        finally:
            if self.process.poll() is None:
                self.stop_proxy()
            self.start_proxy()


if __name__ == "__main__":
    unittest.main()
