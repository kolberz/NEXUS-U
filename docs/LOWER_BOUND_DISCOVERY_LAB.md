# NEXUS-U v2.0 — Lower-Bound Discovery Laboratory

## Purpose

The laboratory converts an open asymptotic lower-bound question into a model-aware, evidence-capped research program. Its first challenge is binary integer multiplication in the multitape Turing-machine model.

The laboratory does **not** claim to solve the open lower bound. It preserves four distinct facts:

1. `O(n log n)` integer multiplication is a proved upper bound in the declared model.
2. The unconditional `Omega(n log n)` lower bound remains open.
3. A published reduction makes the multiplication lower bound conditional on an `Omega(m^2 log m)` matrix-transposition lower bound.
4. Results in online, circuit, RAM, or other restricted models require explicit transfer theorems before they affect the universal target.

## Core records

- **Machine Model Ledger** — encoding, access pattern, online/offline status, randomness, tape or circuit restrictions.
- **Problem Registry** — a problem is inseparable from its computational model and size parameter.
- **Bound Claims** — upper/lower direction, asymptotic expression, scope, assumptions, source, evidence class, status.
- **Reduction Graph** — source problem, target problem, size map, overhead, model preservation, and open premises.
- **Promotion Firewall** — blocks empirical timings, consensus, information counts, or restricted-model results from being promoted into a universal theorem.
- **Theorem Ladder** — ranks restricted results, formalization targets, barrier theorems, and high-leverage open premises.

## Promotion law

A candidate may be promoted only when its evidence class, machine model, scope, and assumptions match the requested theorem status.

```text
empirical timing          != asymptotic lower-bound proof
online lower bound        != offline lower bound
circuit lower bound       != multitape Turing lower bound
proved reduction          != proof of an open premise
restricted theorem        != universal theorem
information count alone   != operation or data-movement lower bound
```

## Built-in challenge

The built-in challenge records:

- Harvey–van der Hoeven's `O(n log n)` upper bound;
- the open matching offline lower bound;
- the 2025 matrix-transposition reduction;
- a published online-model lower bound as restricted progress;
- deliberately invalid promotion attempts used as negative controls;
- a ranked research agenda.

## CLI

```bash
nexus-u lower-bound-lab --output benchmark-results \
  --database .nexus-u/control.db

nexus-u lower-bound-history --database .nexus-u/control.db
```

A custom challenge may be supplied as JSON:

```bash
nexus-u lower-bound-lab challenge.json --output results
```

## HTTP

```text
POST /v1/discovery/lower-bound
GET  /v1/discovery/lower-bounds
GET  /v1/discovery/lower-bounds/{run_id}
```

## Valid progress

The laboratory recognizes narrower progress without confusing it with a solution:

- formalization of a published reduction;
- a new restricted-model lower bound;
- a model-transfer theorem;
- a proof barrier eliminating an invalid strategy;
- a counterexample to a proposed lemma;
- an information-transport invariant with an explicit machine-model proof;
- a proof of the matrix-transposition premise.

## Non-claim

A successful laboratory run means the registry, reduction propagation, promotion firewall, and research-agenda logic behaved correctly. It is not a proof of the open lower bound.
