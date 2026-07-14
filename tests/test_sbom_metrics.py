import json
import tempfile
import unittest
from pathlib import Path

from nexus_u.observability.metrics import MetricsRegistry
from nexus_u.provenance.sbom import build_cyclonedx_sbom


class SbomMetricsTests(unittest.TestCase):
    def test_sbom_has_cyclonedx_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            subject = Path(tmp) / "subject.bin"
            subject.write_bytes(b"x")
            sbom = build_cyclonedx_sbom(subject)
            self.assertEqual(sbom["bomFormat"], "CycloneDX")
            json.dumps(sbom)

    def test_prometheus_metrics(self):
        metrics = MetricsRegistry()
        metrics.inc("example_total", outcome="ok")
        text = metrics.prometheus()
        self.assertIn('example_total{outcome="ok"} 1.0', text)


if __name__ == "__main__":
    unittest.main()
