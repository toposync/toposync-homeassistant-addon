from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StreamingPortContractTest(unittest.TestCase):
    def test_addon_release_version_uses_current_streaming_bundle(self) -> None:
        config = (ROOT / "toposync" / "config.yaml").read_text(encoding="utf-8")
        dockerfile = (ROOT / "toposync" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn('version: "0.4.8"', config)
        self.assertIn("ARG TOPOSYNC_PIP_SPEC=toposync-streaming==0.4.8", dockerfile)

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

    def test_proxy_mode_does_not_declare_hls_as_public_expected_port(self) -> None:
        run_addon = (ROOT / "toposync" / "run_addon.py").read_text(encoding="utf-8")

        self.assertIn('os.environ["TOPOSYNC_STREAMING_HLS_PUBLIC_MODE"] = hls_public_mode', run_addon)
        self.assertIn('if hls_public_mode != "proxy":', run_addon)
        self.assertIn('"TOPOSYNC_EXPECTED_HLS_PORT"', run_addon)
        self.assertIn('"TOPOSYNC_STREAMING_PREFERRED_HLS_PORT"', run_addon)


if __name__ == "__main__":
    unittest.main()
