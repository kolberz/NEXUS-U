# Obligation-Centered Computing

## Original contribution

Traditional workflow engines track tasks. Proof systems track propositions. CI systems track checks. Safety systems track constraints. Provenance systems track events.

NEXUS-U unifies these under one object: the **obligation**.

An obligation is any condition that must be resolved before a claim, artifact, deployment, or transformation may be trusted at a specified level.

## Conservation law

For a transition from state `t` to state `t+1`:

```text
Ω(t+1) = (Ω(t) − D(t)) ∪ N(t) ∪ F(t)
```

Where:

- `Ω(t)` is the set of active obligations;
- `D(t)` contains obligations discharged with evidence;
- `N(t)` contains newly introduced obligations;
- `F(t)` contains explicitly deferred obligations.

The operational invariant is:

```text
Every prior obligation remains represented as an active node or as a terminal node with evidence, a transport relation, or a documented deferral.
```

## Accountable progress

A transition counts as progress only when it does at least one of the following:

1. discharges an obligation with suitable evidence;
2. exposes a previously hidden obligation;
3. decomposes a difficult obligation into accountable sub-obligations;
4. refutes an invalid path with counterevidence;
5. reduces the cost of eventual discharge;
6. defers or escalates the obligation with explicit retry conditions and ownership.

Generating more text, code, plans, or architecture without changing the obligation state is not progress.

## Cross-domain unification

- Formal proof discharges theorem obligations with kernel evidence.
- Software tests discharge executable behavior obligations.
- Safety controllers discharge scoped invariance obligations.
- ZK proofs discharge circuit-adherence obligations.
- SENTINEL exposes physical, numerical, causal, and resource obligations.
- SUTURE-LRC transfers obligations through resource-lowering transformations.
- Discovery creates candidate obligations and resolves them through refutation or verification.
- Creative quality gates discharge intent, structure, and usability obligations before release.

## Epistemic potential

NEXUS-U computes a diagnostic burden:

```text
Φ(X) = Σ severity_weight(obligation) × status_factor(obligation)
```

This is not a probability of error. It indicates how much assumption, deferral, escalation, and unresolved work remains attached to the artifact.

## Geometric interpretation

The state space of NEXUS-U is the space of artifact and obligation configurations. A productive path minimizes:

- unresolved duty;
- risk;
- intent drift;
- proof debt;
- resource cost;

while maximizing evidence gained.

This gives the Geodesic Reasoner a concrete operational meaning: the preferred trajectory is the lowest-cost accountable path from intent to adequately discharged obligations.

## Topological interpretation

A persistent loop is repeated movement through artifact states without net obligation discharge. This can identify:

- tactic oscillation;
- repeated redesign without implementation;
- proof-debt relocation;
- circular requirements;
- recurring resource failures;
- duplicated planning documents that preserve the original blocker.

## Boundary

Obligation conservation guarantees honest bookkeeping, not complete truth. A system can faithfully preserve a bad specification or accept fabricated evidence if evidence producers are not authenticated. The graph therefore complements, rather than replaces, trusted verifiers, empirical validation, security controls, and human judgment.
