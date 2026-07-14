# NEXUS-U v2.2 — Formalized Lower-Bound Search

## Purpose

Version 2.2 promotes the restricted deterministic bit-query lower bound from a narrative certificate to a machine-readable proof object checked by a small, proof-specific verifier.

The release maintains three distinct statuses:

1. `SPECIALIZED_CHECKER_VERIFIED` — the fixed decision-tree sensitivity proof schema is accepted by the NEXUS-U checker.
2. `PROOF_ASSISTANT_READY` — a Lean 4 target file is generated without `sorry`, `admit`, or unreviewed axioms.
3. `KERNEL_VERIFIED` — reserved for successful execution by an external trusted proof-assistant kernel. This status is not emitted when Lean is unavailable.

The universal offline multitape lower bound remains `OPEN`.

## Restricted theorem

For every `n >= 1`, any deterministic adaptive bit-query decision tree that exactly multiplies two `n`-bit unsigned integers has worst-case query depth at least `2n`.

The checker validates the following proof schema:

- Choose `x = y = 2^n - 1`.
- Flipping any bit `i` of `x` changes the product by `2^i * y`, which is nonzero.
- Flipping any bit `i` of `y` changes the product by `2^i * x`, which is nonzero.
- If a sensitive bit is not queried along the witness path, the original and flipped inputs produce identical query transcripts.
- Determinism sends identical transcripts to the same leaf.
- Exactness forbids one leaf from serving two inputs with different products.
- Therefore all `2n` coordinates are queried on the witness path.

This result is scoped to a deterministic individual-bit query model. It is not a multitape Turing-machine lower bound.

## Trust boundary

The specialized checker has a narrow trusted rule set and an embedded checker digest. The release benchmark mutates:

- the claimed bound;
- coordinate coverage;
- the witness;
- the exactness step;
- the machine model;
- the checker identity.

Every mutation must be rejected.

The checker is not presented as a general proof assistant. Its output is `SPECIALIZED_CHECKER_VERIFIED`, never `KERNEL_VERIFIED`.

## Proof-assistant target

The generated Lean source declares:

- bit-vector and sensitivity concepts;
- metadata for the exact-multiplication query target;
- the proposition that a completed development must prove.

It deliberately contains no placeholders or unreviewed axioms. When Lean is unavailable, the target remains generated but externally unverified.

## Transposition reduction formalization plan

The 2025 matrix-transposition route is decomposed into an acyclic obligation graph:

- pin the source and theorem statement;
- define multitape Turing-machine semantics;
- define matrix encoding and transpose semantics;
- define packed integer encoding;
- encode the reduction;
- prove functional correctness;
- prove asymptotic overhead preservation;
- prove machine-model preservation;
- compose the conditional theorem.

The final composition remains conditional because the matrix-transposition lower-bound premise is open.

## Commands

```bash
nexus-u formalized-lower-bound --output benchmark-results
nexus-u formalized-lower-bound \
  --output benchmark-results \
  --database .nexus-u/control.db
nexus-u formalized-lower-bound-history --database .nexus-u/control.db
```

## Non-claims

This release does not claim:

- an unconditional `Omega(n log n)` multiplication lower bound;
- a proof of the matrix-transposition lower bound;
- external Lean kernel verification;
- transfer from the bit-query model to the multitape Turing model.
