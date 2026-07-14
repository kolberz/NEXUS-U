# Obligation Router

NEXUS-U v1.5 adds a cost-aware strategy router over unresolved obligation graphs.

The router does not decide whether a claim is true. It recommends the next evidence-producing action most likely to reduce a specific obligation under a declared cost budget.

## Decision model

For each unresolved obligation, the router:

1. extracts a stable signature from obligation kind, severity, blocking status, source family, and optional routing tags;
2. selects valid candidate strategies from explicit rules;
3. combines prior success estimates with recorded outcomes using a beta-binomial posterior mean;
4. estimates expected cost and weighted-debt reduction;
5. penalizes strategies implicated in repeated failure or oscillation;
6. escalates critical, authority-bound, or stagnant obligations to human review.

The score is an operational ranking, not a probability of truth:

```text
utility = expected discharge value
        + expected debt reduction
        - expected failure cost
        - execution cost
```

## Strategies

- `TEST`
- `COUNTEREXAMPLE_SEARCH`
- `STATIC_ANALYSIS`
- `FORMAL_PROOF`
- `SIMULATION`
- `DOCUMENTATION_SEARCH`
- `DECOMPOSE`
- `REPAIR_IMPLEMENTATION`
- `RESOURCE_LOWERING`
- `HUMAN_REVIEW`
- `DEFER`
- `REJECT`

## Learning boundary

The router learns only from explicit outcome records containing:

- obligation signature;
- selected strategy;
- success or failure;
- elapsed cost;
- weighted obligation-debt change;
- optional artifact and obligation identifiers.

It does not learn from confidence prose or silently infer success from a generated answer.

## Stagnation detection

A route is flagged when recent history shows:

- the same failed strategy repeated at least three times;
- two failed strategies oscillating in an A/B/A/B pattern;
- repeated attempts with no reduction in weighted obligation debt.

High or critical stagnant obligations are escalated to human review. Lower-severity obligations are routed toward decomposition when available.

## CLI

```bash
nexus-u route-obligation --graph artifacts/example.obligations.json --node-id NODE_ID
nexus-u record-route SIGNATURE TEST --success --cost-seconds 1.2 --debt-delta -4
nexus-u routing-stats --signature SIGNATURE
nexus-u routing-benchmark --output benchmark-results
```

## HTTP API

```text
POST /v1/route
POST /v1/routing/outcomes
GET  /v1/routing/stats
GET  /v1/artifacts/{artifact_id}/routes
```

## Safety constraints

The router cannot discharge obligations. It can only recommend strategies. Evidence-producing tools and human authorities remain responsible for resolution. Critical policy duties explicitly marked `requires_human_authority` always route to human review.
