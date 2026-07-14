from __future__ import annotations

from pathlib import Path

from nexus_u.config import task_from_dict
from nexus_u.core.pipeline import Pipeline
from nexus_u.storage.sqlite import ControlStore


def test_partial_pipeline_emits_routing_recommendations(tmp_path: Path):
    store = ControlStore(tmp_path / "control.db")
    task = task_from_dict({
        "intent": "Create output with an unmet success condition",
        "artifact_type": "software",
        "modes": ["SOFTWARE_ENGINEERING"],
        "adapter": "python",
        "success_conditions": ["EXPECTED"],
        "inputs": {"code": "print('OTHER')"},
    })
    record, _ = Pipeline(output_dir=tmp_path / "artifacts", store=store).run(task)
    assert not record.released
    assert record.routing_recommendations
    assert all(item["selected"] for item in record.routing_recommendations)
    persisted = store.get_artifact(record.artifact_id)
    assert persisted is not None
    assert persisted["payload"]["routing_recommendations"]
