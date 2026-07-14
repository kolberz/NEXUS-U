# NEXUS-U 2.6 Validation Report

## Release identity

- NEXUS-U version: `2.6.0`
- Native kernel version: `nexus-kernel-v0.1.0`
- Native kernel status: `NEXUS_KERNEL_VERIFIED`
- Lean compatibility claimed: **no**
- Universal offline integer-multiplication lower bound: **OPEN**

## Test validation

The test matrix was executed in deterministic groups because the monolithic pytest command can
stall in the sandbox's plugin environment.

- Default tests passed: **110**
- End-to-end Reality test passed: **1**
- Total tests passed: **111**
- Native-kernel-focused tests passed: **11**
- Python compilation: passed

No partial dot stream or timed-out aggregate command was counted as a completed test run.

## Native kernel validation

The native kernel benchmark passed **17/17** checks.

Verified properties include:

- closed constructive proof accepted;
- zero axioms in the proof environment;
- canonical proof serialization and replay;
- proof-bundle digest verification;
- exact native-kernel source digest binding;
- beta and delta normalization;
- definitional equality;
- proof-size and reduction resource limits;
- rejection of unbound variables;
- rejection of non-function application;
- rejection of a forged short proof;
- rejection of a mismatched theorem;
- rejection of invalid empty elimination;
- rejection of unknown constants;
- rejection of unknown serialized term tags;
- rejection of kernel-digest substitution;
- rejection of proof-bundle payload tampering.

The trusted native core comprises **667 Python source lines** across:

- `ast.py`
- `ops.py`
- `environment.py`
- `core.py`
- `codec.py`

The trusted-core scan found no use of `eval`, `exec`, pickle, or marshal.

## Clean production evidence

The artifact and benchmark directories were deleted and regenerated from the v2.6 source tree.

- Production workflows reaching `RELEASED`: **4**
- Obligation graphs: acyclic, conservation-valid, and free of unresolved blocking duties
- Benchmark families regenerated: Reality Loop, Obligation Router, Federated Evidence,
  Tension-Driven Discovery, Discovery Trials, Independent Challenge, Preregistered Reproduction,
  Lower-Bound Laboratory, Active Search, Formalized Lower Bound, Cross-Kernel theorem,
  Lean bridge, Kernel Witness Federation, and Native NEXUS Kernel
- Signed benchmark envelopes: generated with the v2.6 release key

## Clean-wheel validation

A new isolated virtual environment installed the built wheel and successfully executed:

```text
nexus-u --version
nexus-u nexus-kernel-benchmark
nexus-u kernel-check nexus-kernel-proof.json
```

The installed wheel reproduced the exact native-kernel digest and accepted the canonical proof
bundle.

## Evidence boundary

`NEXUS_KERNEL_VERIFIED` means the proof object was accepted by the exact NEXUS Kernel source digest
under its declared calculus and environment. It does not mean:

- Lean kernel verified;
- compatible with Lean proof terms;
- independently proved metatheoretically sound;
- hardened for hostile multi-tenant operation without an OS sandbox;
- the unrestricted `Omega(n log n)` multiplication lower bound is solved.

The Python interpreter and runtime remain part of the implementation trusted computing base.
