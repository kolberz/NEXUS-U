# Production Rollout

## Promotion path

1. Pull requests run unit tests, bytecode compilation, task validation, obligation-aware demos, package builds, and the release gate.
2. Merge to `main` creates a continuously deployable revision.
3. Tag `vX.Y.Z` triggers package creation, provenance generation, container build, GHCR push, and GitHub Release publication.
4. Pin the immutable container digest in `deploy/k8s/deployment.yaml` and deploy to staging.
5. Staging smoke tests must verify both runtime health and obligation conservation.
6. Production promotion requires a released artifact, a conservation-valid obligation graph, a verified audit chain, and provenance attestations.

## Release invariants

The release gate blocks when any released artifact lacks:

- its obligation graph;
- evidence for discharged or refuted obligations;
- an acyclic dependency structure;
- zero unresolved high/critical blocking obligations;
- a passing `RELEASED` promotion decision;
- provenance attestations for the artifact and graph.

## Service endpoints

- `GET /health`
- `GET /health/ready`
- `GET /metrics`
- `GET /v1/capabilities`
- `POST /v1/plan`
- `POST /v1/run`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `GET /v1/artifacts/{artifact_id}/obligations`
- `GET /v1/artifacts/{artifact_id}/obligation-summary`
- `GET /v1/obligations`
- `POST /v1/obligations/verify`

## Required repository controls

- Protect `main` and require CI.
- Require signed commits or verified merge commits.
- Restrict release tags.
- Enable secret scanning and dependency review.
- Pin third-party actions by commit SHA in hardened environments.
- Store production signing keys outside general-purpose runners.
- Require approval for intentional deferral of critical obligations.

## Storage

The SQLite control plane indexes artifacts, obligation nodes, and obligation edges. For horizontally scaled deployments, replace SQLite with a transactional database while preserving:

- immutable node identifiers;
- append-only graph events;
- relation integrity;
- artifact/graph atomicity;
- audit and provenance hashes.

## Production limitations

The included Python adapter executes trusted code in an isolated process with a timeout, but it is not a strong multi-tenant sandbox. Untrusted execution requires a hardened worker such as a restricted container, microVM, or external job system.

The obligation graph guarantees accountable state transitions. It cannot prove that the human specification is complete or that every evidence producer is trustworthy. Authenticate evidence sources and retain explicit environmental assumptions.

## Deployment

The `Deploy` workflow deploys releases to staging and then to a protected production environment. Configure:

- secret `KUBE_CONFIG`;
- variable `NEXUS_BASE_URL`;
- manual approval on the production environment;
- immutable image references.

## Rollback

```bash
kubectl rollout undo deployment/nexus-u
kubectl rollout status deployment/nexus-u --timeout=300s
```

After rollback, run `scripts/smoke_test.py`. Preserve the failed deployment's artifact, audit, and obligation graph as incident evidence rather than deleting it.

## External verifier workers

Lean and Dafny may run locally in trusted deployments. Higher-assurance deployments should isolate them as pinned workers. Absence or failure of an external verifier creates an explicit unresolved obligation and a partial artifact; it never emits simulated proof evidence.


## Reality Loop release invariant

Version 1.4 requires the built-in Git delivery benchmark to match every expected
outcome before a release manifest is approved. The benchmark report and its signed
envelope are provenance-attested alongside package and obligation-graph artifacts.

The `git_delivery` adapter operates only on disposable clones. It records the base
commit, changed files, complete diff, and diff digest. Commands are executed without
a shell, but they remain trusted workload execution. Run untrusted candidates in
separate workers or containers with restricted credentials and network access.
