# Obligation Graph Engine

## Purpose

The Obligation Graph Engine turns NEXUS-U from a linear workflow into an operating system for accountable progress.

The graph's governing equation is:

```text
Ω(t+1) = (Ω(t) − discharged) ∪ introduced ∪ deferred
```

Because graph nodes are immutable and never deleted, an obligation cannot disappear from history. Its state may change only through an audited operation.

## Node kinds

| Kind | Meaning |
|---|---|
| `INTENT` | Original purpose that must remain preserved |
| `SPECIFICATION` | Formal or executable interpretation of intent |
| `REQUIREMENT` | Functional or nonfunctional completion duty |
| `ASSUMPTION` | Declared premise or environmental condition |
| `CLAIM` | Statement requiring evidence |
| `TEST` | Executable validation duty |
| `PROOF` | Formal proof obligation |
| `SAFETY` | Scoped safety or feasibility requirement |
| `POLICY` | Governance or compliance requirement |
| `RESOURCE` | Time, memory, energy, or deployment budget |
| `RISK` | Risk-model or uncertainty obligation |
| `PROVENANCE` | Audit, identity, and reproduction requirement |
| `EVIDENCE` | Evidence object supporting or contradicting obligations |

## Statuses

- `OPEN`
- `ACKNOWLEDGED`
- `DISCHARGED`
- `DEFERRED`
- `REFUTED`
- `ESCALATED`
- `TRANSFERRED`

`DISCHARGED` and `REFUTED` require evidence. `DEFERRED` requires a reason and retry conditions. `TRANSFERRED` requires an explicit refinement, decomposition, or transport edge.

## Operations

```text
CREATE_OBLIGATION
ADD_EVIDENCE
ADD_RELATION
DISCHARGE_OBLIGATION
REFUTE_OBLIGATION
DEFER_OBLIGATION
ESCALATE_OBLIGATION
TRANSFER_OBLIGATION
```

## Promotion calculus

An artifact may be promoted to `RELEASED` only when:

1. conservation verification passes;
2. the graph is acyclic;
3. required intent, requirement, claim, policy, and safety duties exist and are satisfied;
4. at least one evidence node exists;
5. no high or critical blocking duty remains unresolved.

Formal proof promotion additionally requires a proof node and appropriate kernel evidence.

## API examples

Inspect graph summary:

```bash
nexus-u obligations --graph artifacts/example.obligations.json
```

Verify conservation and release readiness:

```bash
nexus-u verify-obligations artifacts/example.obligations.json --target RELEASED
```

Query open blocking duties:

```bash
curl 'http://localhost:8080/v1/obligations?status=OPEN&blocking=true'
```

Validate a graph supplied by another system:

```bash
curl -X POST http://localhost:8080/v1/obligations/verify \
  -H 'Content-Type: application/json' \
  --data @artifacts/example.obligations.json
```

## Security and epistemic boundary

The graph verifies accountability of transitions. It does not guarantee that:

- the specification captures the correct human values;
- the environment assumptions are true;
- an evidence generator is trustworthy unless independently authenticated;
- a risk model captures unknown hazards.

It prevents silent obligation loss; it does not manufacture complete knowledge.
