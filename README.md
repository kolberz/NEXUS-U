# NEXUS-U v2.6 — Native Kernel Production

NEXUS-U is an obligation-centered runtime for discovery, construction, formal verification, safety review, provenance, and controlled release. Version 2.6 adds the native production kernel while retaining independent cross-checks against the arithmetic sensitivity certificate and replayable Lean bridge.

The first production challenge is binary integer multiplication. The laboratory records the proved `O(n log n)` upper bound, preserves the unconditional matching lower bound as `OPEN`, and represents the matrix-transposition route as a `CONDITIONAL_THEOREM` until its premise is proved. The active-search layer then generates and attacks proof routes before ranking them by expected obligation reduction.

```bash
nexus-u lower-bound-lab --output benchmark-results --database .nexus-u/control.db
nexus-u lower-bound-search --output benchmark-results --database .nexus-u/control.db
nexus-u lower-bound-search-history --database .nexus-u/control.db
nexus-u formalized-lower-bound --output benchmark-results --database .nexus-u/control.db
nexus-u formalized-lower-bound-history --database .nexus-u/control.db
```

The search engine blocks timings, Landauer-only arguments, online-to-offline transfers, and circuit-to-Turing transfers before ranking. It also emits a scoped `DERIVED_RESTRICTED` certificate showing that deterministic exact bit-query multiplication has worst-case query depth at least `2n`. This does not prove the open multitape `Omega(n log n)` target. Agreement between the arithmetic certificate checker and the logical microkernel remains required, and CI independently builds the replayable project with the pinned Lean kernel.

See `docs/LOWER_BOUND_DISCOVERY_LAB.md`, `docs/ACTIVE_LOWER_BOUND_SEARCH.md`, and `docs/FORMALIZED_LOWER_BOUND_SEARCH.md`.

## Core law

> An unresolved obligation may be discharged with evidence, transformed with an explicit transport relation, deferred with retry conditions, refuted with counterevidence, or escalated—but never silently erased.

Every run now emits four linked artifacts:

- the constructed artifact record;
- a hash-chained execution audit;
- a signed or unsigned evidence bundle;
- an immutable obligation graph.

## Obligation graph

The graph records:

- intent;
- assumptions;
- specifications;
- requirements;
- claims;
- tests and proof duties;
- safety and policy gates;
- resource limits;
- evidence and provenance.

Edges describe dependency, refinement, decomposition, transfer, support, discharge, verification, contradiction, and blocking relationships.

Release is denied when:

- a high or critical blocking obligation remains open, deferred, or escalated;
- a discharged or refuted obligation lacks evidence;
- a transformation loses its transport relation;
- the graph contains a dependency cycle;
- conservation verification fails.

## Obligation Router

The router recommends the next action for every unresolved duty. It combines explicit domain rules with recorded outcome histories and never discharges an obligation itself.

```bash
nexus-u route-obligation --graph artifacts/<artifact-id>.obligations.json --node-id <node-id>
nexus-u record-route <signature> TEST --success --cost-seconds 1.0 --debt-delta -4
nexus-u routing-stats --signature <signature>
nexus-u routing-benchmark --output benchmark-results
nexus-u federation-benchmark --output benchmark-results
nexus-u tension-benchmark --output benchmark-results
nexus-u independent-challenge --output benchmark-results
nexus-u preregistered-reproduction --output benchmark-results/reproduction
nexus-u lower-bound-lab --output benchmark-results
nexus-u lower-bound-search --output benchmark-results
nexus-u formalized-lower-bound --output benchmark-results
```

The built-in benchmark covers testing, formal proof, resource lowering, stagnation escalation, human authority, and invalid-premise rejection.

## Federated Evidence

Federated promotion counts independent evidence, not merely signatures. Correlated submissions from the same provenance group cannot satisfy an independence quorum. Conflicting evidence, security vetoes, missing authority roles, and unresolved cross-repository dependencies block approval.

```bash
nexus-u federation-evaluate examples/federation_release.json --database .nexus-u/control.db
nexus-u federation-benchmark --output benchmark-results
nexus-u tension-benchmark --output benchmark-results
```

## Tension-Driven Discovery

Discovery begins where independently supported obligations refuse to fit one explanation. NEXUS-U detects the conflict, preserves both evidence streams, proposes bounded explanatory repairs, and chooses the declared experiment expected to reduce hypothesis uncertainty per unit cost and risk.

```bash
nexus-u tension-discover examples/tension_discovery.json --output tension-results --database .nexus-u/control.db
nexus-u tension-benchmark --output benchmark-results
nexus-u tension-history --database .nexus-u/control.db
```

The tension score is a prioritization metric, not a truth probability. See `docs/TENSION_DRIVEN_DISCOVERY.md`.

## Kernel Verification Bridge

NEXUS-U v2.6 includes a replayable Lean project for the generic sensitivity-to-query lower-bound theorem. The bridge:

- pins `leanprover/lean4:v4.29.1`;
- emits a complete Lean source file with no `sorry`, `admit`, `axiom`, or `unsafe`;
- records all source hashes in a replay manifest;
- rejects missing, wrong-version, or untrusted toolchain identities;
- promotes to `KERNEL_VERIFIED` only after the pinned Lean command succeeds;
- otherwise reports `PROOF_PROJECT_READY_KERNEL_PENDING`.

```bash
nexus-u kernel-bridge --output benchmark-results --database .nexus-u/control.db
```

The kernel theorem is scoped to deterministic path certificates: all-sensitive coordinates must all be queried. The multiplication sensitivity instantiation and the universal offline `Omega(n log n)` lower bound remain separate obligations.

## Quick start

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .

nexus-u validate examples/hello_python.json
nexus-u run examples/hello_python.json --output artifacts --database .nexus-u/control.db
nexus-u verify-obligations artifacts/<artifact-id>.obligations.json
nexus-u obligations --artifact-id <artifact-id> --database .nexus-u/control.db
nexus-u reality-benchmark --builtin --output benchmark-results
nexus-u routing-benchmark --output benchmark-results
nexus-u federation-benchmark --output benchmark-results
nexus-u tension-benchmark --output benchmark-results
```

Or:

```bash
make test
make demo
make release
```

## HTTP API

```bash
export NEXUS_U_API_TOKEN="replace-with-a-long-random-secret"
nexus-u serve --port 8080
```

PowerShell:

```powershell
$env:NEXUS_U_API_TOKEN = "replace-with-a-long-random-secret"
nexus-u serve --port 8080
```

The server listens on `127.0.0.1` by default. Health endpoints are public; all other routes, including metrics, require `Authorization: Bearer <token>`. For an explicitly local development-only server, set `NEXUS_U_ALLOW_UNAUTHENTICATED=true`. Bind to `0.0.0.0` only behind appropriate network controls.

Core routes:

```text
GET  /health
GET  /health/ready
GET  /metrics
POST /v1/run
POST /v1/plan
POST /v1/jobs
GET  /v1/jobs/{job_id}
GET  /v1/artifacts
GET  /v1/artifacts/{artifact_id}
GET  /v1/artifacts/{artifact_id}/obligations
GET  /v1/artifacts/{artifact_id}/obligation-summary
GET  /v1/artifacts/{artifact_id}/obligation-metrics
GET  /v1/obligations?status=OPEN&blocking=true
POST /v1/obligations/verify
POST /v1/route
POST /v1/routing/outcomes
GET  /v1/routing/stats
GET  /v1/artifacts/{artifact_id}/routes
POST /v1/federation/evaluate
GET  /v1/federation/evidence
GET  /v1/federation/decisions
POST /v1/discovery/tension
GET  /v1/discovery/tensions
GET  /v1/discovery/tensions/{run_id}
POST /v1/discovery/reproduction
POST /v1/discovery/lower-bound
GET  /v1/discovery/lower-bounds
GET  /v1/discovery/lower-bounds/{run_id}
POST /v1/discovery/lower-bound-search
GET  /v1/discovery/lower-bound-searches
GET  /v1/discovery/lower-bound-searches/{run_id}
GET  /v1/discovery/reproductions
GET  /v1/discovery/reproductions/{run_id}
```

## Task manifest

```json
{
  "intent": "Produce and verify a Python artifact",
  "artifact_type": "software",
  "modes": ["SOFTWARE_ENGINEERING"],
  "adapter": "python",
  "success_conditions": ["READY"],
  "assumptions": ["Python 3.11 or newer"],
  "initial_obligations": [
    {
      "statement": "The output must not contain a placeholder",
      "kind": "POLICY",
      "severity": "HIGH",
      "blocking": true
    }
  ],
  "inputs": {"code": "print('READY')"}
}
```

Initial blocking obligations must be explicitly discharged by an integration or left visible; they are never auto-cleared.

## Epistemic potential

NEXUS-U computes a weighted unresolved-obligation burden:

```text
Epistemic potential = Σ severity_weight × status_factor
```

The score is diagnostic, not a truth probability. It helps detect obligation accumulation, stalled work, and releases carrying excessive unresolved debt.

## Status integrity

NEXUS-U never promotes a claim beyond its evidence. Execution evidence can support `EXECUTION_VERIFIED`; only a real proof-kernel adapter may support `KERNEL_VERIFIED`.

## Integrations

Built-in adapters include:

- trusted Python execution;
- document validation;
- deterministic evaluator-driven discovery;
- optional Lean/Lake verification;
- optional Dafny verification;
- Git-backed proof-carrying software delivery.

Missing external verifiers produce explicit partial results rather than simulated proof success.

## Production boundary

The included Python adapter is for trusted workloads and local validation. It is not a multi-tenant security sandbox. Deployments accepting untrusted code must use isolated workers, restricted credentials, network controls, and external policy enforcement.

See:

- `docs/OBLIGATION_GRAPH.md`
- `docs/REALITY_LOOP.md`
- `docs/OBLIGATION_ROUTER.md`
- `docs/FEDERATED_EVIDENCE.md`
- `docs/ACTIVE_LOWER_BOUND_SEARCH.md`
- `docs/KERNEL_VERIFICATION_BRIDGE.md`
- `docs/PRODUCTION.md`
- `docs/INTEGRATIONS.md`
- `VALIDATION.md`

## Cross-kernel restricted theorem

Run:

```bash
nexus-u cross-kernel --output benchmark-results
```

The command combines an arithmetic sensitivity certificate with an independent typed natural-deduction proof microkernel. A successful result is labeled `CROSS_KERNEL_SCOPED_VERIFIED`; it is not labeled Lean-kernel verified, and the universal offline `Omega(n log n)` lower bound remains open.

## Native NEXUS Kernel — v2.6

NEXUS-U now includes its own small dependent-type checker. It verifies replayable proof objects
without relying on a Lean installation. The kernel is intentionally narrower than Lean and uses a
separate proof format.

```bash
nexus-u nexus-kernel-benchmark --output benchmark-results
nexus-u kernel-check benchmark-results/nexus-kernel-proof.json
```

The reference theorem is checked with no axioms. A successful result is labeled
`NEXUS_KERNEL_VERIFIED`, not `LEAN_KERNEL_VERIFIED`. See
[`docs/NEXUS_KERNEL.md`](docs/NEXUS_KERNEL.md) for the calculus and trust boundary.
