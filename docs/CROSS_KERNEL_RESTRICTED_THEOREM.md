# NEXUS-U v2.4 — Cross-Kernel Restricted Theorem

This release separates the restricted multiplication decision-tree result into two independently checked components:

1. **Arithmetic sensitivity certificate** — verifies the all-ones witness, bit-flip deltas, positivity, exact `2*n` coordinate coverage, and decision-tree composition rules.
2. **Natural-deduction microkernel** — checks a typed proof term for the logical path argument: an omitted sensitive coordinate preserves the transcript, exactness forces equal output, and sensitivity yields contradiction.

The two certificates are hash-bound into one composition report. The microkernel is intentionally small and scoped; it is not represented as Lean or as a universal proof-assistant kernel.

## Status boundary

- Restricted deterministic bit-query theorem: `CROSS_KERNEL_SCOPED_VERIFIED`
- Lean bridge: `PROOF_PROJECT_READY_KERNEL_PENDING` unless a pinned Lean toolchain actually accepts it
- Offline multitape-Turing-machine `Omega(n log n)` lower bound: `OPEN`

This design reduces single-checker risk without inflating the theorem's scope.
