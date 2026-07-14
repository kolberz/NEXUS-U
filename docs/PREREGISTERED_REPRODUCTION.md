# Preregistered Reproduction

NEXUS-U v1.9 adds an immutable reproduction protocol for discovery benchmarks.

## Purpose

The protocol prevents evaluation decisions from changing after results are visible. Before inference begins it seals:

- corpus, labels, and source-registry hashes;
- deterministic sampling seed and algorithm;
- selected case identifiers;
- primary metrics and success criteria;
- evaluator identities, distinct key identifiers, and quorum;
- engine version and challenge scope.

The protocol hash is computed over the complete preregistration payload. Any later mutation invalidates it.

## Label firewall

Inference workers receive only the selected blind corpus. Held-out labels are stored separately and opened only after prediction files are written and hashed. Each evaluator result binds the sealed prediction hash to the protocol hash.

## Evaluator model

The bundled benchmark runs three evaluator-specific Python subprocesses and signs their results with distinct local HMAC test identities. This verifies process isolation, deterministic replay, signature handling, quorum aggregation, and tamper detection.

It does **not** establish external institutional independence. The report therefore emits:

```json
{"external_independence_claimed": false}
```

Production evaluators should use independently administered asymmetric identities, isolated infrastructure, and out-of-band protocol custody.

## Deterministic sampling

Cases are ranked by:

```text
SHA-256(seed + ":" + case_id)
```

The first `sample_size` cases are selected. This is deterministic across machines and does not depend on source ordering.

## Replay bundle

Every run creates:

```text
reproduction-bundle/
├── preregistration.json
├── blind/corpus.json
├── scoring/labels.json
├── source-registry.json
├── evaluator-registry.json
├── MANIFEST.json
└── README.md
```

The blind corpus and scoring labels remain physically separated so a third party can run inference, seal outputs, and then score.

## Promotion status

A successful local run receives `PROCESS_REPRODUCED`, not `INDEPENDENTLY_REPRODUCED`. Promotion to independent reproduction requires signed reports from genuinely separate organizations or evaluators whose infrastructure and keys are not controlled by the original system operator.
