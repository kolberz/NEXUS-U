# External Integrations

NEXUS-U v1.1 keeps discovery and provenance operational with no third-party runtime dependencies. Formal verification and deployment tools are optional capabilities.

## Capability discovery

```bash
nexus-u capabilities
```

The command reports installed tools without promoting unavailable capabilities into evidence.

## Lean

Use adapter `lean` with `inputs.source`. NEXUS-U rejects `sorry` and `admit` before invocation. A successful Lean invocation contributes `kernel` evidence. If Lean is unavailable, the run terminates as partial with an explicit obligation.

For a Lake project, set `inputs.project_dir` and `inputs.file_name`. The adapter uses the pinned project environment.

## Dafny

Use adapter `dafny` with `inputs.source`. A successful `dafny verify` run contributes `conditional_proof` evidence because the result is relative to the declared specifications and verifier assumptions.

## Evaluator-driven discovery

Use adapter `discovery` with candidate metrics, objective weights, hard constraints, and an optional minimum score. This is the local production analogue of evaluator-driven candidate evolution: candidate generation may be external, but promotion remains deterministic and auditable.

## Adapter plugins

Third-party Python packages may register adapters through the `nexus_u.adapters` entry-point group. Plugin load failures are isolated and recorded by the registry instead of preventing built-in adapters from starting.

## Provenance

```bash
nexus-u attest dist/package.whl
nexus-u verify-attestation dist/package.whl.intoto.json dist/package.whl
```

NEXUS-U emits an in-toto Statement v1 using the SLSA provenance v1 predicate. The local verifier checks structure, builder identity, subject name, and SHA-256 digest. Signing remains an external trust operation; use organizational signing infrastructure such as Cosign where required.

## Orchestration

`nexus-u plan task.json` emits a provider-neutral plan. The plan can be executed by the built-in pipeline or translated into an external workflow engine without changing NEXUS-U evidence semantics.
