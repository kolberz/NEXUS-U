# Federated Evidence

NEXUS-U v1.6 extends obligation-centered computing across organizational and repository boundaries.

## Core rule

A federation decision is not the number of signatures attached to a claim. It is a scoped judgment over:

- authenticated actors;
- distinct organizations;
- authority roles;
- independent provenance groups;
- trust weights;
- unresolved conflicting evidence;
- veto rights;
- cross-repository dependencies.

Two signatures derived from the same CI run count as two attestations but only one independent evidence group.

## Evidence submission

Every submission binds an actor, organization, obligation, verdict, evidence digest, provenance group, scope, and signature.

Verdicts are:

- `SUPPORTS`
- `REFUTES`
- `INCONCLUSIVE`

The bundled HMAC implementation is a deterministic local reference. Production federations should use asymmetric signing, workload identity, or an external trust service.

## Quorum policy

A policy can require:

- a minimum number of organizations;
- a minimum aggregate trust weight;
- a minimum count of independent provenance groups;
- required roles such as reviewer or verifier;
- veto roles such as security;
- no unresolved conflicts;
- exact cross-system dependency identifiers.

Approval is denied when any required dimension is missing.

## Conflict semantics

Supporting and refuting evidence on the same obligation produces `CONFLICT` when conflict-free policy is enabled. A refutation by a veto-authorized actor produces `BLOCKED` even when ordinary quorum is otherwise met.

The runtime does not average contradictory evidence into a false consensus.

## Cross-repository obligations

Graphs are namespaced by repository before federation. Cross-repository links identify exact source and target obligations and may require the target graph digest. Missing nodes or digest mismatches remain unresolved and block federation validity.

## Sovereignty boundary

Organizations retain authority over local obligations. A global policy may only require evidence or approval for scopes declared in its contract. Actor authority scopes are checked before accepting evidence.

## API

```text
POST /v1/federation/evaluate
GET  /v1/federation/evidence
GET  /v1/federation/decisions
```

## CLI

```bash
nexus-u federation-evaluate examples/federation_release.json --database .nexus-u/control.db
nexus-u federation-benchmark --output benchmark-results
```

## Security boundary

Federated approval proves only that the declared policy was satisfied by authenticated evidence inputs. It does not establish that organizations are independent in the social or corporate sense, that their evidence is truthful, or that the policy fully captures the real-world decision.
