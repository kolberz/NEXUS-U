# Discovery Trials

NEXUS-U v1.7 adds blind, provenance-bearing evaluation for Tension-Driven Discovery.

## Purpose

Synthetic anomaly cases prove that the engine executes its own rules. They do not show that the method can preserve source identity, abstain on agreement, or detect contradictions across heterogeneous artifacts. Discovery Trials add that missing boundary.

A trial suite contains source claims, provenance groups, scope, and evidence direction. Expected labels remain in the evaluator and are not passed to the discovery engine. The corpus hash excludes those labels.

## Trial cycle

```text
source artifacts
  -> normalized claims
  -> signed/provenance-aware evidence ledger
  -> blind tension inference
  -> minimal repair hypotheses
  -> discriminating experiment recommendation
  -> post-hoc scoring against held-out labels
```

## Metrics

- precision: detected tensions that were expected;
- recall: expected tensions detected;
- specificity: no-tension controls correctly ignored;
- F1 score;
- tension-kind accuracy;
- experiment-match count;
- false discoveries;
- missed tensions;
- correct abstentions.

A no-tension control is not a trivial case. It verifies that the engine does not manufacture novelty from multiple compatible sources.

## Corpus integrity

The report binds a SHA-256 digest of the unlabeled corpus. The digest includes claims, source identifiers, provenance groups, scope, and evidence direction. It excludes expected labels and scoring hints.

The built-in corpus is derived from real architecture and audit artifacts in the NEXUS research program. It is curated and therefore does not establish general scientific-discovery superiority. Its purpose is to validate provenance preservation, blind inference, contradiction classification, and clean abstention.

## Commands

```bash
nexus-u discovery-trials --output benchmark-results
nexus-u discovery-trials path/to/suite.json --database .nexus-u/control.db
nexus-u trial-history --database .nexus-u/control.db
```

## HTTP

```text
POST /v1/discovery/trials
GET  /v1/discovery/trials
GET  /v1/discovery/trials/{run_id}
```

## Honest boundary

Discovery Trials do not prove that a generated hypothesis is true. They establish that the engine can:

1. detect independently sourced tensions without seeing labels;
2. preserve provenance and scope;
3. abstain when evidence is compatible;
4. propose a discriminating next test;
5. expose its error rates.
