from __future__ import annotations

import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class StreamingPortContractTest(unittest.TestCase):
    def test_addon_release_version_uses_current_streaming_bundle(self) -> None:
        config = (ROOT / "toposync" / "config.yaml").read_text(encoding="utf-8")
        dockerfile = (ROOT / "toposync" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('version: "0.7.7"', config)
        self.assertIn("ARG TOPOSYNC_PIP_SPEC=toposync-streaming==0.7.6", dockerfile)
        self.assertIn("  - amd64", config)
        self.assertIn("  - aarch64", config)

    def test_config_exposes_streaming_ports_and_ingress_stream(self) -> None:
        config = (ROOT / "toposync" / "config.yaml").read_text(encoding="utf-8")

        self.assertIn("ingress_stream: true", config)
        for port in ("18756/tcp", "18758/tcp", "18760/tcp", "18762/udp"):
            self.assertIn(f"  {port}: null", config)
            self.assertIn(f"  {port}: Toposync", config)
        self.assertNotIn("  18759/tcp:", config)

    def test_dockerfile_exposes_webrtc_udp_contract_port(self) -> None:
        dockerfile = (ROOT / "toposync" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("EXPOSE 18756 18757 18758 18760", dockerfile)
        self.assertIn("EXPOSE 18762/udp", dockerfile)
        self.assertNotIn("EXPOSE 18756 18757 18758 18759 18760", dockerfile)

    def test_dockerfile_bundles_go2rtc_for_mse(self) -> None:
        dockerfile = (ROOT / "toposync" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("ARG GO2RTC_VERSION=", dockerfile)
        self.assertIn("ENV TOPOSYNC_STREAMING_GO2RTC_PATH=/usr/local/bin/go2rtc", dockerfile)
        self.assertIn("from toposync_ext_streaming.streaming import GO2RTC_VERSION", dockerfile)
        self.assertIn("go2rtc_linux_{arch}", dockerfile)
        self.assertIn("amd64|x86_64) go2rtc_arch=\"amd64\"", dockerfile)
        self.assertIn("aarch64|arm64) go2rtc_arch=\"arm64\"", dockerfile)

    def test_startup_defaults_use_bundled_go2rtc_when_present(self) -> None:
        fake_fastapi = types.ModuleType("fastapi")
        fake_fastapi.FastAPI = object
        fake_fastapi.Request = object
        fake_starlette_responses = types.ModuleType("starlette.responses")
        fake_starlette_responses.StreamingResponse = object
        with mock.patch.dict(
            sys.modules,
            {"fastapi": fake_fastapi, "starlette.responses": fake_starlette_responses},
        ):
            from toposync import run_addon

        with tempfile.TemporaryDirectory() as temp_dir:
            binary_path = Path(temp_dir) / "go2rtc"
            binary_path.write_bytes(b"")
            snapshot_path = Path(temp_dir) / "addon-network.json"
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch.object(run_addon, "GO2RTC_BINARY_PATH", binary_path),
                mock.patch.object(run_addon, "ADDON_NETWORK_SNAPSHOT_PATH", snapshot_path),
            ):
                run_addon._seed_streaming_env_defaults()

                self.assertEqual(os.environ["TOPOSYNC_STREAMING_GO2RTC_PATH"], str(binary_path))

    def test_proxy_mode_does_not_declare_hls_as_public_expected_port(self) -> None:
        run_addon = (ROOT / "toposync" / "run_addon.py").read_text(encoding="utf-8")

        self.assertIn('os.environ["TOPOSYNC_STREAMING_HLS_PUBLIC_MODE"] = hls_public_mode', run_addon)
        self.assertIn('if hls_public_mode != "proxy":', run_addon)
        self.assertIn('"TOPOSYNC_EXPECTED_HLS_PORT"', run_addon)
        self.assertIn('"TOPOSYNC_STREAMING_PREFERRED_HLS_PORT"', run_addon)

    def test_supervisor_port_snapshot_records_published_network(self) -> None:
        fake_fastapi = types.ModuleType("fastapi")
        fake_fastapi.FastAPI = object
        fake_fastapi.Request = object
        fake_starlette_responses = types.ModuleType("starlette.responses")
        fake_starlette_responses.StreamingResponse = object
        with mock.patch.dict(
            sys.modules,
            {"fastapi": fake_fastapi, "starlette.responses": fake_starlette_responses},
        ):
            from toposync import run_addon

        class FakeResponse:
            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "data": {
                            "slug": "574b2a03_toposync",
                            "version": "0.7.7",
                            "ingress": True,
                            "ingress_stream": True,
                            "network": {
                                "18756/tcp": 18756,
                                "18758/tcp": 18758,
                                "18760/tcp": 18760,
                                "18762/udp": 18762,
                            },
                        }
                    }
                ).encode("utf-8")

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_path = Path(temp_dir) / "addon-network.json"
            with (
                mock.patch.dict(os.environ, {"SUPERVISOR_TOKEN": "token", "SUPERVISOR": "http://supervisor"}),
                mock.patch.object(run_addon, "ADDON_NETWORK_SNAPSHOT_PATH", snapshot_path),
                mock.patch("urllib.request.urlopen", return_value=FakeResponse()) as urlopen_mock,
            ):
                run_addon._write_addon_network_snapshot()

            url = str(urlopen_mock.call_args.args[0].full_url)
            self.assertEqual(url, "http://supervisor/addons/self/info")
            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["network"]["18756/tcp"], 18756)
            self.assertEqual(payload["network"]["18762/udp"], 18762)
            self.assertTrue(payload["ingress_stream"])


if __name__ == "__main__":
    unittest.main()
