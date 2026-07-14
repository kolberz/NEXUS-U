from pathlib import Path

from nexus_u.benchmark.kernel_receipts import run_kernel_receipt_benchmark
from nexus_u.formalization.kernel_bridge import KernelBridgeEngine, PINNED_LEAN_TOOLCHAIN, PINNED_LEAN_VERSION
from nexus_u.formalization.kernel_receipts import (
    KernelQuorumStatus,
    KernelReceiptFederation,
    KernelRunnerIdentity,
    build_receipt_request,
    make_reference_receipt,
)


def _request(tmp_path: Path):
    project = KernelBridgeEngine.write_project(tmp_path / "project")
    return build_receipt_request(project_dir=project, theorem="allSensitive_forces_allQueried", toolchain=PINNED_LEAN_TOOLCHAIN, version_fragment=PINNED_LEAN_VERSION)


def test_local_quorum_never_claims_external_reproduction(tmp_path: Path) -> None:
    request = _request(tmp_path)
    federation = KernelReceiptFederation(request)
    for suffix in ("a", "b"):
        runner = KernelRunnerIdentity(f"runner-{suffix}", f"org-{suffix}", f"group-{suffix}", f"key-{suffix}", platform_family="linux" if suffix == "a" else "macos")
        federation.register_runner(runner, secret=f"secret-{suffix}")
        federation.submit(make_reference_receipt(request, runner, salt=suffix))
    decision = federation.evaluate()
    assert decision.status == KernelQuorumStatus.LOCAL_PROCESS_QUORUM
    assert decision.external_independence_claimed is False
    assert decision.theorem_status == "KERNEL_RECEIPT_QUORUM_PENDING_EXTERNAL"
    assert decision.universal_target_status == "OPEN"


def test_conflicting_receipts_block_quorum(tmp_path: Path) -> None:
    request = _request(tmp_path)
    federation = KernelReceiptFederation(request)
    for suffix, accepted in (("a", True), ("b", False)):
        runner = KernelRunnerIdentity(f"runner-{suffix}", f"org-{suffix}", f"group-{suffix}", f"key-{suffix}")
        federation.register_runner(runner, secret=f"secret-{suffix}")
        federation.submit(make_reference_receipt(request, runner, accepted=accepted, salt=suffix))
    assert federation.evaluate().status == KernelQuorumStatus.CONFLICT


def test_tampered_receipt_is_rejected(tmp_path: Path) -> None:
    request = _request(tmp_path)
    federation = KernelReceiptFederation(request)
    runner = KernelRunnerIdentity("runner", "org", "group", "key")
    federation.register_runner(runner, secret="secret")
    receipt = make_reference_receipt(request, runner)
    federation.sign_local(receipt)
    receipt.source_sha256 = "0" * 64
    ok, errors = federation.verify(receipt)
    assert ok is False
    assert any("source_sha256 mismatch" in error for error in errors)


def test_kernel_receipt_benchmark(tmp_path: Path) -> None:
    report, path = run_kernel_receipt_benchmark(output_dir=tmp_path, signing_secret="secret")
    assert report.summary()["pass_rate"] == 1.0
    assert report.summary()["quorum_status"] == "LOCAL_PROCESS_QUORUM"
    assert path.is_file()
    assert (tmp_path / "kernel-receipt-federation.signed.json").is_file()
