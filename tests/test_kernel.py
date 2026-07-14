from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_u.benchmark import make_proof_bundle, reference_proof, reference_theorem, run_benchmark, verify_bundle
from nexus_u.kernel import App, Empty, Kernel, KernelError, Lam, Sort, Var, decode_term, encode_term


def test_reference_proof_checks() -> None:
    Kernel().check(reference_proof(), reference_theorem())


def test_beta_normalization() -> None:
    identity = Lam(Sort(0), Var(0))
    assert Kernel().definitionally_equal(App(identity, Empty()), Empty())


def test_codec_round_trip() -> None:
    proof = reference_proof()
    assert decode_term(encode_term(proof)) == proof


def test_unbound_variable_rejected() -> None:
    with pytest.raises(KernelError):
        Kernel().infer(Var(0))


def test_bundle_replay() -> None:
    verify_bundle(make_proof_bundle())


def test_benchmark_passes() -> None:
    result = run_benchmark()
    assert result["summary"]["check_count"] == 17
    assert result["summary"]["checks_passed"] == 17
    assert result["summary"]["all_checks_passed"] is True
    assert result["summary"]["axiom_count"] == 0
