# NEXUS Kernel v0.1

NEXUS Kernel is a small, auditable dependent-type proof checker embedded in NEXUS-U 2.6.
It is inspired by the trust architecture of systems such as Lean, but it is **not Lean**, does not
parse Lean syntax, and cannot verify arbitrary Lean projects.

## Trusted calculus

The native core checks nameless de Bruijn proof terms with:

- predicative universes `Sort u`;
- dependent function types `Pi`;
- lambda introduction and application;
- transparent and opaque constant declarations;
- local `let` definitions;
- binary sums and non-dependent case elimination;
- the empty type and empty elimination;
- beta, delta, zeta, and sum-case reduction;
- definitional equality by normalization.

No general recursion, reflection, macros, metaprogram execution, quotient types, inductive-family
compiler, proof irrelevance, universe polymorphism, or Lean compatibility layer is claimed.

## Trust boundary

Trusted implementation files:

```text
src/nexus_u/kernel/ast.py
src/nexus_u/kernel/ops.py
src/nexus_u/kernel/environment.py
src/nexus_u/kernel/core.py
src/nexus_u/kernel/codec.py
```

The following are untrusted conveniences whose outputs are rechecked:

- named surface elaboration;
- theorem generators;
- proof search and AI output;
- JSON producers;
- benchmark code;
- CLI and HTTP layers.

## Reference theorem

The release checks a constructive generic lemma used by the decision-tree lower-bound argument.
In informal notation:

```text
queried, same, equal : Proposition
not_equal : equal -> False
preserve : (queried -> False) -> same
path_exact : same -> equal
decide : queried + (queried -> False)
------------------------------------------------
queried
```

The proof performs case analysis on explicit decidability. In the negative branch, transcript
preservation and path exactness imply `equal`, contradicting `not_equal`. Empty elimination then
produces `queried`.

The proof has no axioms in its environment. Decidability is an explicit premise, not a hidden
classical rule.

## Proof bundles

A proof bundle contains:

- the exact kernel version and source digest;
- theorem and proof terms in canonical JSON;
- proof and theorem size statistics;
- the complete axiom list;
- scope and non-compatibility declarations;
- a bundle digest.

Replay:

```bash
nexus-u nexus-kernel-benchmark --output benchmark-results
nexus-u kernel-check benchmark-results/nexus-kernel-proof.json
```

## Security controls

The kernel enforces limits on:

- term node count;
- syntax-tree depth;
- reduction steps;
- universe level;
- serialized decoder depth.

The trusted core does not use `eval`, `exec`, pickle, or marshal. Definitions are checked before
being installed, and recursive self-reference is unavailable because a declaration is added only
after its value has been checked in the prior environment.

## Status semantics

`NEXUS_KERNEL_VERIFIED` means only:

> The serialized proof term was accepted by this exact NEXUS Kernel source digest under its
> declared environment and calculus.

It does not mean:

- accepted by Lean;
- accepted by another proof assistant;
- the NEXUS Kernel is metatheoretically proven sound;
- the unrestricted integer-multiplication lower bound is solved.

The universal offline `Omega(n log n)` multiplication lower bound remains `OPEN`.
