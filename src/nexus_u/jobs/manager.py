from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid
from typing import Any, Callable

from nexus_u.config import task_from_dict
from nexus_u.core.pipeline import Pipeline
from nexus_u.observability.metrics import METRICS
from nexus_u.storage.sqlite import ControlStore


class JobManager:
    def __init__(self, store: ControlStore, pipeline_factory: Callable[[], Pipeline] | None = None, workers: int = 2) -> None:
        self.store = store
        self.pipeline_factory = pipeline_factory or (lambda: Pipeline(output_dir=Path("artifacts"), store=store))
        self.executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="nexus-u-job")

    def submit(self, raw_task: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        self.store.create_job(job_id, raw_task)
        METRICS.inc("nexus_u_jobs_submitted_total")
        self.executor.submit(self._run, job_id, raw_task)
        return job_id

    def _run(self, job_id: str, raw_task: dict[str, Any]) -> None:
        self.store.update_job(job_id, status="RUNNING")
        METRICS.set_gauge("nexus_u_jobs_active", 1)
        try:
            task = task_from_dict(raw_task)
            record, path = self.pipeline_factory().run(task)
            self.store.update_job(
                job_id,
                status="SUCCEEDED" if record.released else "COMPLETED_WITH_OBLIGATIONS",
                artifact_id=record.artifact_id,
                artifact_path=str(path),
            )
            METRICS.inc("nexus_u_jobs_completed_total", outcome="released" if record.released else "partial")
        except Exception as exc:
            self.store.update_job(job_id, status="FAILED", error=f"{type(exc).__name__}: {exc}")
            METRICS.inc("nexus_u_jobs_completed_total", outcome="failed")
        finally:
            METRICS.set_gauge("nexus_u_jobs_active", 0)
