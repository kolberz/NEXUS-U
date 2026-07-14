# Tension-Driven Discovery

NEXUS-U does not treat novelty as unusual output. It treats discovery as the resolution of a measurable conflict among independently supported obligations.

## Discovery invariant

```text
Contradictory evidence
→ explicit tension
→ minimal explanatory repairs
→ discriminating experiment
→ posterior update
→ measured tension reduction
```

An evidence conflict becomes a discovery target only when both sides are authenticated and provenance-aware. Repeated signatures from one underlying source do not create independent evidence.

## Tension score

The reference score combines:

- balance between supporting and refuting evidence;
- total trust weight;
- independent provenance groups.

It is a routing and prioritization score, not a probability that either claim is true.

## Minimal explanatory repairs

The engine searches a bounded repair vocabulary:

- narrow the scope or boundary conditions;
- detect calibration or labeling error;
- introduce a hidden variable or dependency;
- revise an incomplete model;
- identify a resource regime transition;
- escalate a genuinely normative conflict to human authority.

Every hypothesis carries complexity and newly created obligations. A hypothesis is valuable when it predicts substantial tension resolution without laundering the conflict into a larger unexplained assumption.

## Discriminating experiment selection

For hypotheses `H` and experiment `e`, the engine computes expected information gain:

```text
IG(e) = entropy(prior) - expected entropy(posterior | outcome, e)
```

The production utility is:

```text
utility(e) = IG(e) / (cost(e) × (1 + risk(e)))
```

The selected experiment is the least costly declared test expected to separate the competing explanations. This does not guarantee scientific truth; it identifies the best next information-producing action under the supplied model.

## Measured reduction

When an experiment result is supplied, the engine updates hypothesis probabilities and calculates the reduction in unresolved tension. A result can leave tension unresolved. Negative or ambiguous results remain in the evidence record.

## Security and epistemic limits

- Signed evidence can still be false.
- Provenance-group independence must be externally auditable.
- Likelihood models can be misspecified.
- Information gain is conditional on the candidate hypothesis set.
- A successful experiment can discriminate explanations without proving the surviving one universally.
- Human ethical or legal disagreements are not converted into empirical questions unless a legitimate measurable distinction exists.

## CLI

```bash
nexus-u tension-discover examples/tension_discovery.json \
  --output tension-results \
  --database .nexus-u/control.db

nexus-u tension-history --database .nexus-u/control.db
nexus-u tension-benchmark --output benchmark-results
```

## API

```text
POST /v1/discovery/tension
GET  /v1/discovery/tensions
GET  /v1/discovery/tensions/{run_id}
```
