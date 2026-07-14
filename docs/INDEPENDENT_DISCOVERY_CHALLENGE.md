# Independent Discovery Challenge

NEXUS-U v1.8 adds an external-corpus evaluation layer. It is deliberately narrower than an open-domain scientific discovery claim.

## Design

The challenge has three physically separate inputs:

1. `external-corpus.json` — unlabeled cases and attributed evidence.
2. `external-labels.json` — held-out scoring labels.
3. `source-registry.json` — dataset versions, citations, licenses, upstream IDs, and snapshot methods.

Inference is completed and sealed before the label file is consulted. The release gate hashes all three inputs separately.

## External sources

- CLIMATE-FEVER: real-world climate claims with supporting, refuting, and insufficient evidence.
- SciFact: expert-written scientific claims with evidence-bearing abstracts and rationales.
- ContractNLI: document-level natural-language inference over contracts.

Only compact attributed records required for the benchmark are bundled. Full upstream datasets are not redistributed.

## Scope

This challenge evaluates:

- detection of independently annotated support/refute tension;
- abstention when evidence is one-sided or inconclusive;
- source and provenance preservation;
- label isolation;
- reproducible hashing and signing.

It does not evaluate:

- open-domain retrieval;
- novel scientific hypothesis generation;
- full-document legal reasoning;
- model performance on complete upstream test sets;
- superiority over published dataset baselines.

## Run

```bash
nexus-u independent-challenge \
  --output benchmark-results \
  --secret "$NEXUS_U_SIGNING_KEY"
```

Custom corpus, label, and registry files may be supplied independently.
