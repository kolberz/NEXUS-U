# Composite Platform Architecture

NEXUS-U does not attempt to replace mature verification and provenance systems. It supplies the cross-domain control plane that binds them together.

| Plane | NEXUS-U responsibility | External integration |
|---|---|---|
| Discovery | Candidate schema, evaluator gate, negative results | Search/evolution agents |
| Formal proof | Evidence policy, task routing, artifact capture | Lean/Lake |
| Verified software | Contract and evidence capture | Dafny |
| Orchestration | Provider-neutral plans and state machine | Enterprise workflow engines |
| Provenance | Claim-to-artifact binding | in-toto/SLSA, optional signing |
| Deployment | Release gate and rollout evidence | Docker/Kubernetes |

The integration rule is: external systems may produce evidence, but only the NEXUS-U claim gate assigns an epistemic status to the resulting claim.
