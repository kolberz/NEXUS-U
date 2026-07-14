# Kernel Witness Federation

NEXUS-U v2.5 externalizes the last unresolved proof obligation without pretending that a local bespoke checker is the Lean kernel.

A **kernel receipt request** fixes:

- the theorem and project identifier;
- the complete project and source hashes;
- the exact Lean toolchain;
- the exact build command;
- the universal target status.

A runner returns a signed receipt containing its organization, provenance group, platform, Lean version, executable digest, command, exit code, and output digests.

## Status boundary

`LOCAL_PROCESS_QUORUM` means multiple independently configured local reference runners agreed. It validates receipt mechanics only.

`FEDERATED_KERNEL_REPRODUCED` requires externally administered runner identities, externally verifiable signatures, independent provenance groups, and successful matching kernel receipts.

The included release does not emit `FEDERATED_KERNEL_REPRODUCED`. It emits:

```text
KERNEL_RECEIPT_QUORUM_PENDING_EXTERNAL
```

The unrestricted offline integer-multiplication lower bound remains `OPEN`.

## Stable toolchain pin

The replay project is pinned to:

```text
leanprover/lean4:v4.29.1
```

## External replay

1. Extract the generated kernel-receipt project.
2. Install the pinned Lean toolchain.
3. Run `lake build`.
4. Produce a receipt tied to the request hashes.
5. Sign the receipt using an independently managed identity.
6. Submit it with at least one independently administered receipt from another organization.
