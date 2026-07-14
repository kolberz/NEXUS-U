## 2.4.0 — Cross-Kernel Restricted Theorem

- Added a typed natural-deduction proof microkernel.
- Added an explicit proof term for the sensitivity-to-query logical argument.
- Added five adversarial proof-term mutations.
- Hash-bound the logical proof certificate to the independent arithmetic sensitivity certificate.
- Added `nexus-u cross-kernel` and a signed benchmark report.
- Preserved the Lean bridge as kernel-pending and the universal lower bound as open.

# Changelog

## 2.3.0 — Kernel Verification Bridge

- Added a replayable, dependency-free Lean 4 project for the generic all-sensitive-coordinates theorem.
- Added a pinned Lean toolchain identity and executable digest capture.
- Added a release-safe execution boundary: verified only when the pinned toolchain identity and proof-project command both succeed.
- Added explicit pending, untrusted-toolchain, rejection, and execution-failure statuses.
- Added a replay manifest, CI kernel job, static proof lint, schema, CLI, HTTP, SQLite history, tests, signed benchmark, provenance, and release-gate integration.
- Preserved the multiplication sensitivity instantiation and universal offline `Omega(n log n)` lower bound as open obligations.

## 2.2.0 — Formalized Lower-Bound Search

- Added a specialized proof-certificate checker for the deterministic exact bit-query multiplication lower bound.
- Added a narrow trusted-rule ledger, checker source digest, arithmetic sanity sweeps, and six adversarial certificate mutations.
- Added a generated Lean 4 formalization target containing no `sorry`, `admit`, or unreviewed axioms.
- Added an explicit status boundary between specialized-checker verification, proof-assistant readiness, and external kernel verification.
- Added an acyclic proof-obligation decomposition for formalizing the matrix-transposition reduction.
- Added CLI, HTTP, SQLite history, schema, tests, signed benchmark, CI, provenance, and release-gate integration.
- Preserved the universal offline `Omega(n log n)` target and transposition premise as open.


## 2.0.0 — Lower-Bound Discovery Laboratory

- Added a machine-model ledger for offline multitape Turing, online multitape, and bounded-coefficient circuit settings.
- Added typed upper/lower-bound claims, proof statuses, evidence classes, and source provenance.
- Added a reduction graph that preserves open premises and propagates only conditional consequences.
- Added a proof-promotion firewall for empirical, consensus, information-counting, online/offline, circuit/Turing, restricted/universal, and reduction-premise gaps.
- Added a ranked theorem ladder and negative-knowledge obstruction catalog.
- Added a built-in integer-multiplication challenge based on the proved `O(n log n)` upper bound and the matrix-transposition reduction route.
- Added CLI, HTTP, SQLite, schema, tests, signed benchmark, CI, release-gate, and provenance integration.
- Added an explicit non-claim: a successful laboratory run does not solve the open universal lower bound.

## 1.9.0 — Preregistered Reproduction

- Added immutable preregistration protocols with corpus, label, registry, sample, metric, evaluator, quorum, and success-criteria hashes.
- Added language-independent deterministic sampling by SHA-256 rank.
- Added evaluator-specific subprocess inference with labels absent from worker inputs.
- Added sealed prediction hashes, distinct signed evaluator identities, quorum aggregation, and exact agreement checks.
- Added mutation and signature-tamper detection.
- Added third-party replay bundles with physically separated blind and scoring directories.
- Added SQLite, CLI, HTTP, schema, CI, release-gate, and provenance integration.
- Added explicit `PROCESS_REPRODUCED` status and prohibition on claiming external evaluator independence from local replay.

## 1.6.0 — Tension-Driven Discovery and Federated Evidence

- Added authenticated multi-organization evidence submissions.
- Added organization, trust-weight, role, and independent-provenance quorum rules.
- Added conflict detection and security/compliance veto support.
- Added actor authority scopes and explicit human-authority requirements.
- Added cross-repository obligation graph namespacing, digest binding, and dependency validation.
- Added SQLite persistence for federation evidence and decisions.
- Added CLI and HTTP evaluation/query interfaces.
- Added a signed six-case benchmark covering approval, correlated evidence, conflict, veto, missing dependency, and missing authority.
- Release automation now requires Federated Evidence benchmark invariants.
- Added provenance-aware obligation-tension detection across supporting and refuting evidence.
- Added bounded minimal-repair hypothesis generation.
- Added expected-information-gain experiment selection with cost and risk penalties.
- Added posterior updates and measurable tension-reduction reports.
- Added SQLite, CLI, and HTTP interfaces for discovery histories.
- Added a signed six-case benchmark that outperforms a static novelty baseline.
- Release automation now requires Tension-Driven Discovery benchmark invariants.

## 1.5.0 — Obligation Router

- Added cost-aware routing over unresolved obligation graphs.
- Added Bayesian outcome learning from explicit strategy results.
- Added strategy cost, predicted discharge, and weighted-debt scoring.
- Added repeated-failure, oscillation, and no-progress detection.
- Added critical and human-authority escalation policy.
- Added persistent SQLite routing history and statistics.
- Added route recommendations to partial and rejected artifact records.
- Added CLI commands for routing, outcome recording, statistics, and benchmarking.
- Added HTTP routing endpoints and rollout smoke coverage.
- Added a signed six-case router benchmark that materially outperforms a static tests-only router.
- Release automation now requires both Reality Loop and Obligation Router benchmark invariants.

## 1.4.0 — Reality Loop

- Added Git-backed proof-carrying software delivery.
- Added obligation-delta metrics and a tests-only baseline benchmark.
- Bound signed benchmark evidence into release promotion.

## 1.3.0 — Obligation-Centered Production

- Added immutable obligation graphs and conservation-aware release gates.

## 2.6.0 — Native NEXUS Kernel

- Added a native predicative dependent-type proof kernel.
- Added de Bruijn core terms, universes, dependent functions, sums, empty elimination, definitions,
  normalization, and definitional equality.
- Added canonical JSON proof bundles and deterministic replay.
- Added explicit axiom accounting and kernel source hashing.
- Added resource limits for proof size, depth, universes, decoding, and normalization.
- Added mutation testing against forged proofs, unknown constants, invalid elimination, digest
  substitution, and malformed serialized terms.
- Added `nexus-kernel-benchmark` and `kernel-check` CLI commands.
- Added a release-gate invariant requiring the axiom-free reference proof and mutation suite.
- Preserved the distinction between NEXUS Kernel verification and Lean kernel verification.
