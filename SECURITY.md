# Security Policy

## Supported version

Security fixes are applied to the current major release.

## Reporting

Do not disclose suspected vulnerabilities in public issues. Use the repository security-advisory workflow or the private contact configured by the repository owner.

## Execution boundary

The bundled Python adapter is for trusted workloads. It uses a separate interpreter process and timeout, but it is not a hardened sandbox. Untrusted code must run in a dedicated container, microVM, or external worker with network, filesystem, syscall, CPU, and memory controls.

## Obligation-graph trust boundary

The graph prevents silent obligation loss only when its evidence sources and persistence layer are trustworthy. Production deployments must:

- authenticate evidence producers;
- authorize status transitions;
- prevent direct database edits outside the service identity;
- preserve append-only graph events;
- sign or transparently publish evidence bundles;
- review intentional deferral or transfer of critical duties;
- reject graph imports containing cycles, dangling edges, or terminal duties without evidence.

A valid graph proves accountable bookkeeping relative to supplied evidence. It does not prove that the specification is complete or that the evidence itself is truthful.

## Release controls

Production releases should use protected environments, immutable image digests, provenance attestations, vulnerability scanning, and signed images. Rotate verification and deployment credentials regularly.


## Git delivery execution boundary

The Git delivery adapter creates a disposable local clone and invokes commands from
the task manifest with `shell=False`. This reduces command-injection surface but is
not a hostile-code sandbox. Do not expose arbitrary repository paths or commands to
untrusted callers without isolated workers, filesystem confinement, network policy,
short-lived credentials, and operating-system resource limits.

## Routing-history integrity

Routing outcomes influence future strategy recommendations. Production deployments must authenticate outcome writers, preserve artifact and obligation identifiers, and prevent untrusted tenants from poisoning shared routing history. Separate stores or signed outcome envelopes are recommended for mutually untrusted projects. Route recommendations never constitute evidence and cannot discharge obligations.


## Federated evidence trust boundary

The bundled HMAC signer is a local reference mechanism, not a multi-organization public-key infrastructure. Production federations must use asymmetric identities or workload identity, protect key rotation and revocation, and bind actor authority to externally governed organization records.

Evidence independence is represented by declared provenance groups. A malicious coalition can lie about provenance unless groups are derived from signed build identities, independent data sources, or externally auditable execution records. Quorum is not a substitute for source validation.

Conflicting evidence must remain visible until resolved under an explicit policy. Administrators must not delete refutations or change actor roles to manufacture approval. Cross-repository dependencies should be pinned by immutable digest rather than branch name.


## Tension-discovery trust boundary

Tension-Driven Discovery is conditional on the supplied evidence, provenance groups, hypothesis set, priors, and experiment likelihoods. Production deployments must authenticate evidence producers, derive independence from auditable execution identities, and prevent a coalition from manufacturing contradictory submissions solely to trigger research work.

Experiment likelihoods and costs are model inputs rather than verified facts. Review them before irreversible or high-risk execution. A reduction in hypothesis entropy does not prove the surviving hypothesis, and a tension score is not a probability of truth. Preserve refuting and inconclusive evidence even after a candidate explanation becomes dominant.


## Preregistered-reproduction trust boundary

The bundled evaluator identities use fixed HMAC secrets solely for local regression and release-gate testing. They do not provide organizational independence, public verifiability, revocation, or compromise isolation. Production reproduction must replace them with independently administered asymmetric keys or workload identities.

A protocol hash prevents unnoticed mutation only when protocol custody and the hashing implementation are trusted. Independent evaluators should receive the sealed protocol through an append-only registry or transparency log. Blind corpus and scoring labels must be access-controlled separately.

Process isolation reduces accidental label leakage but is not a hostile sandbox. External evaluators should use separate machines or accounts, independent network/storage boundaries, and reproducible container or VM images.


## Lower-bound laboratory trust boundary

The laboratory is a research-governance and proof-status system, not an automated proof of open complexity lower bounds. Source records, machine-model declarations, reductions, and candidate metadata are inputs and must be reviewed. A valid laboratory report proves only that the registry and promotion rules were applied consistently.

Production deployments must:

- pin primary-source identities and preserve publication metadata;
- prevent users from changing a machine model after evidence has been attached;
- require explicit transfer theorems across online/offline, circuit/Turing, randomized/deterministic, RAM/Turing, or restricted/universal boundaries;
- preserve open premises in reduction graphs;
- treat finite tests, performance measurements, information counts, and consensus as non-proof evidence;
- prohibit any status transition to `PROVED` without an accepted proof artifact or reviewed published proof;
- retain rejected proof routes as negative knowledge rather than deleting them.

The built-in source registry contains canonical links and summaries but does not bundle third-party paper contents.

## Active lower-bound search trust boundary

Proof-route files are untrusted research inputs. Production deployments should:

- require signed route registries or content-addressed review;
- prevent route metadata from changing machine-model identities or evidence status silently;
- keep benchmark expectations outside inference and ranking code;
- reject routes that request universal status from empirical, restricted, online, circuit, or thermodynamic evidence without a proved transfer;
- treat symbolic and finite certificates as scoped evidence, never kernel verification;
- preserve blocked routes as negative knowledge rather than deleting their failure rationale.


## Formalization trust boundary

The decision-tree certificate checker is a proof-specific verifier, not a replacement for Lean, Isabelle, or Coq. Its accepted status is `SPECIALIZED_CHECKER_VERIFIED`. `KERNEL_VERIFIED` requires successful execution by an external trusted kernel. Generated proof-assistant targets must contain no placeholders or unreviewed axioms. Mutation tests guard against stronger false bounds, omitted coordinates, witness substitution, missing exactness steps, machine-model laundering, and checker substitution.


## Kernel bridge trust boundary

The Lean bridge trusts only a configured executable whose `--version` output matches the pinned version and whose proof-project command exits successfully. The executable path and digest are recorded. A malicious binary can still spoof its identity; production deployments should obtain Lean through a verified package or container supply chain and bind that provenance to the release. Toolchain absence, identity mismatch, and compiler rejection never become proof success.

## Native NEXUS Kernel

The native kernel is security-sensitive code and should be treated as a separate trusted computing
base. Reports should include the exact kernel source digest. Do not accept proof bundles created for
a different digest without an explicit migration and replay review.

The initial kernel is not hardened against hostile multi-tenant use beyond deterministic resource
limits. Run untrusted proof checking inside an operating-system sandbox with CPU, memory, file,
process, and network restrictions. The kernel intentionally contains no general recursion or dynamic
code execution, but Python and its runtime remain part of the implementation TCB.

`NEXUS_KERNEL_VERIFIED` must never be translated to `LEAN_KERNEL_VERIFIED` or universal theorem
verification.
