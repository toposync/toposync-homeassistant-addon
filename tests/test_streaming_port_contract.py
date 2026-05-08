from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StreamingPortContractTest(unittest.TestCase):
    def test_config_exposes_streaming_ports_and_ingress_stream(self) -> None:
        config = (ROOT / "toposync" / "config.yaml").read_text(encoding="utf-8")

        self.assertIn("ingress_stream: true", config)
        for port in ("18756/tcp", "18758/tcp", "18759/tcp", "18760/tcp", "18762/udp"):
            self.assertIn(f"  {port}: null", config)
            self.assertIn(f"  {port}: Toposync", config)

    def test_dockerfile_exposes_webrtc_udp_contract_port(self) -> None:
        dockerfile = (ROOT / "toposync" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("EXPOSE 18756 18757 18758 18759 18760", dockerfile)
        self.assertIn("EXPOSE 18762/udp", dockerfile)


if __name__ == "__main__":
    unittest.main()
