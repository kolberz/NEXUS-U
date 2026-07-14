# NEXUS-U v2.3 — Kernel Verification Bridge

## Purpose

The bridge converts the restricted lower-bound argument into a replayable Lean project without pretending that source generation is kernel verification.

## Kernel theorem

For a finite Boolean input, suppose a deterministic path certificate is exact for every input agreeing with a witness on the queried coordinates. If every coordinate is sensitive at that witness, every coordinate must be queried.

The proof uses only the following contradiction:

1. assume a sensitive coordinate is not queried;
2. choose its sensitivity witness;
3. the witness agrees on every queried coordinate;
4. path exactness forces equal output;
5. sensitivity requires unequal output.

## Status lattice

```text
STATIC_CHECK_FAILED
UNTRUSTED_TOOLCHAIN
KERNEL_REJECTED
KERNEL_EXECUTION_FAILED
PROOF_PROJECT_READY_KERNEL_PENDING
KERNEL_VERIFIED
```

Only the final state is kernel evidence.

## Replay project

Generated under `benchmark-results/kernel-bridge/`:

- `lean-toolchain`;
- `lakefile.toml`;
- `NexusUKernelBridge/AllSensitive.lean`;
- `verify.sh`;
- `.github/workflows/kernel-check.yml`;
- `replay-manifest.json`.

## Scope

The theorem proves the generic path-certificate bridge. It does not by itself prove:

- that the selected multiplication encoding is sensitive in all `2n` coordinates;
- a lower bound for unrestricted multitape Turing machines;
- the open `Omega(n log n)` multiplication lower bound.

## Production rule

If the pinned toolchain exists and rejects the project, release is blocked. If it is absent, the release may carry a signed pending replay obligation but cannot emit `KERNEL_VERIFIED`.
