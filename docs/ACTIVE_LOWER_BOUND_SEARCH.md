# NEXUS-U v2.1 — Active Lower-Bound Search

## Purpose

The v2.0 laboratory protected the boundary between proved, conditional, restricted, empirical, and open lower-bound claims. v2.1 adds an active search layer that proposes proof routes, attacks them before ranking, derives scoped results when possible, and measures expected obligation reduction.

The system does **not** claim the open universal lower bound for offline integer multiplication.

## Search invariant

```text
Generate route
→ expose machine model and assumptions
→ attack scope, evidence, reversibility, and transfer
→ block or preserve conditionally
→ rank by expected obligation reduction
→ emit scoped progress certificate
```

Novelty alone is never sufficient for priority.

## Proof-route portfolio

The built-in portfolio includes:

- machine-checking the published transposition reduction;
- multiscale communication cuts for matrix transposition;
- crossing-sequence arguments in an oblivious restricted model;
- a barrier theorem for bare information-counting arguments;
- empirical, Landauer, online-to-offline, and circuit-transfer routes used as adversarial controls.

## Restricted result

The engine derives the following scoped theorem:

> Any deterministic bit-query decision tree computing exact multiplication of two n-bit integers has worst-case query depth at least 2n.

Witness: `x = y = 2^n - 1`.

At this input, every input bit is sensitive. A deterministic path omitting any sensitive bit would follow the same path after flipping that bit while the correct product changes. Therefore all `2n` bits must be queried on that path.

The release includes finite sanity checks for `n = 1..16`. The certificate is labeled `DERIVED_RESTRICTED`, not `KERNEL_VERIFIED`, and it does not imply the open `Omega(n log n)` multitape Turing lower bound.

## Ranking

Each route receives a score based on:

- leverage;
- novelty;
- tractability;
- estimated execution cost;
- unresolved proof obligations;
- inherited model and evidence obstructions.

Blocked routes receive zero priority. Conditional routes retain their open premises. Formalization-ready routes can be sent to Lean, Isabelle, or another trusted checker without changing their epistemic status beforehand.

## Interfaces

```bash
nexus-u lower-bound-search --output benchmark-results
nexus-u lower-bound-search-history --database .nexus-u/control.db
```

HTTP:

```text
POST /v1/discovery/lower-bound-search
GET  /v1/discovery/lower-bound-searches
GET  /v1/discovery/lower-bound-searches/{run_id}
```

## Promotion boundary

Valid progress includes:

- a correct restricted-model theorem;
- a formalization-ready reduction;
- a falsified proof route;
- a barrier theorem ruling out a weak proof method;
- a conditional route with all premises visible.

No generated route may promote the universal target beyond `OPEN` without a complete accepted proof in the exact declared model.
