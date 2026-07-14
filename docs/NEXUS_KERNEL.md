# NEXUS Kernel v0.1

NEXUS Kernel is a small, auditable dependent-type proof checker embedded in NEXUS-U 2.6. It is inspired by the trust architecture of systems such as Lean, but it is **not Lean**, does not parse Lean syntax, and cannot verify arbitrary Lean projects.

## Trusted calculus

The native core checks nameless de Bruijn proof terms with predicative universes, dependent function types, lambda introduction and application, transparent and opaque constants, local `let` definitions, binary sums, non-dependent case elimination, the empty type, empty elimination, and beta/delta/zeta/sum-case reduction.

## Trust boundary

Trusted implementation files:

```text
src/nexus_u/kernel/ast.py
src/nexus_u/kernel/ops.py
src/nexus_u/kernel/environment.py
src/nexus_u/kernel/core.py
src/nexus_u/kernel/codec.py
```

Proof search, named elaboration, JSON producers, benchmark code, CLI code, and AI-generated terms are untrusted conveniences whose outputs are rechecked by the kernel.

## Reference theorem

```text
queried, same, equal : Proposition
not_equal : equal -> False
preserve : (queried -> False) -> same
path_exact : same -> equal
decide : queried + (queried -> False)
------------------------------------------------
queried
```

The proof performs case analysis on explicit decidability. The negative branch derives `equal`, contradicts `not_equal`, and eliminates the empty type to produce `queried`.

## Status semantics

`NEXUS_KERNEL_VERIFIED_RECOVERED` means the proof object was accepted by the exact reconstructed kernel source digest. It does not mean Lean acceptance, arbitrary Lean compatibility, metatheoretical soundness, or a solution of the unrestricted multiplication lower bound.
