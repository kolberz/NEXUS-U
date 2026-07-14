from pathlib import Path

from nexus_u.benchmark.reproduction import run_preregistered_reproduction
from nexus_u.storage.sqlite import ControlStore


def test_reproduction_persistence(tmp_path: Path):
    report, _ = run_preregistered_reproduction(output_dir=tmp_path / "out", sample_size=8)
    store = ControlStore(tmp_path / "control.db")
    store.record_reproduction(report)
    stored = store.get_reproduction(report.run_id)
    assert stored is not None
    assert stored["status"] == "PROCESS_REPRODUCED"
    assert stored["payload"]["summary"]["reproduced"] is True
    listed = store.list_reproductions(report.protocol.protocol_hash)
    assert len(listed) == 1
