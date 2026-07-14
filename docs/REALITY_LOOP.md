# NEXUS-U Reality Loop

The Reality Loop is the first empirical vertical for Obligation-Centered Computing.
It compares a conventional delivery pipeline—candidate patch followed by tests—with
NEXUS-U's Git-backed delivery contract.

## Baseline

The baseline applies the candidate to a disposable Git workspace and runs only the
declared tests. It intentionally ignores security checks, rollback requirements,
intent-preservation checks, provenance, and unresolved-obligation accounting.

## NEXUS-U path

The NEXUS-U path applies the same candidate and evaluates:

- tests;
- build commands;
- security commands;
- required files and required behavior markers;
- prohibited patterns;
- rollback readiness;
- Git base commit, changed-file list, and diff digest;
- release policy, safety review, provenance, and obligation conservation.

Each check becomes an obligation with evidence. Failed checks generate explicit
remediation obligations and block release.

## Built-in benchmark

```bash
nexus-u reality-benchmark --builtin --output benchmark-results
```

The built-in suite contains four candidates:

1. Complete delivery — baseline passes and NEXUS-U releases.
2. Hidden dynamic-evaluation risk — tests pass, NEXUS-U blocks.
3. Missing rollback contract — tests pass, NEXUS-U blocks.
4. Intent drift — tests pass, NEXUS-U blocks.

A release is approved only when the benchmark matches all expected outcomes and
demonstrates at least one hidden obligation caught beyond the tests-only baseline.

## Obligation metrics

Each artifact records:

- obligations created, discharged, refuted, deferred, escalated, and transferred;
- evidence count;
- active-obligation delta;
- gross obligation weight introduced;
- final weighted obligation debt;
- resolved weight and resolution ratio;
- mean and maximum discharge time;
- unresolved critical obligations.

These metrics measure accountable transformation, not probability of truth.

## Security boundary

The Git adapter executes commands from trusted task manifests in disposable local
workspaces. It is not a hostile multi-tenant sandbox. Production deployments that
accept untrusted code must execute jobs in isolated workers with restricted
credentials, network policy, filesystem controls, and resource limits.
