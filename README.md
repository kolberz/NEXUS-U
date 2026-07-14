# NEXUS-U v2.6 — Native Kernel Recovery

NEXUS-U is an obligation-centered computing runtime. Version 2.6 introduced a small auditable dependent-type proof checker, **NEXUS Kernel v0.1**, and a mutation-resistant proof-bundle benchmark.

## Recovery status

This repository was reconstructed from the preserved v2.6 release specification, validation report, release manifest, benchmark evidence, and SHA-256 inventory after the original ZIP archive bytes were unavailable to the publishing session.

It is **not claimed to be byte-identical** to `NEXUS-U_v2.6_Native_Kernel_Production.zip`. The original archive identity remains recorded in `NEXUS-U_v2.6_SHA256SUMS.txt`. Reconstructed code and regenerated proof bundles use the status `NEXUS_KERNEL_VERIFIED_RECOVERED` to avoid conflating them with the archived release digest.

## What is implemented

- predicative universes;
- dependent function types and lambdas;
- de Bruijn variables;
- transparent/opaque constants;
- local `let` reduction;
- binary sums and non-dependent elimination;
- the empty type and empty elimination;
- beta, delta, zeta, and sum-case normalization;
- definitional equality;
- canonical JSON proof serialization;
- proof-bundle and exact-kernel-source digest binding;
- resource bounds and adversarial mutation checks.

## Install and run

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .
pytest
nexus-u nexus-kernel-benchmark --output benchmark-results
nexus-u kernel-check benchmark-results/nexus-kernel-proof.json
```

Expected benchmark summary:

```json
{
  "all_checks_passed": true,
  "axiom_count": 0,
  "check_count": 17,
  "checks_passed": 17,
  "external_lean_compatible": false,
  "kernel_status": "NEXUS_KERNEL_VERIFIED_RECOVERED",
  "universal_offline_lower_bound_status": "OPEN"
}
```

## Epistemic boundary

A successful result means that a serialized proof term was accepted by the exact source digest in this repository under its declared calculus. It does **not** mean Lean compatibility, external proof-assistant acceptance, metatheoretical soundness, hostile multi-tenant hardening, or resolution of the unrestricted integer-multiplication lower bound.
