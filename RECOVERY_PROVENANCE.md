# Recovery provenance

This repository is a transparent source-level reconstruction of NEXUS-U v2.6 created after the archived ZIP was indexed but its raw bytes were unavailable to the publishing runtime.

## Archived identity

- Archive: `NEXUS-U_v2.6_Native_Kernel_Production.zip`
- SHA-256: `4b13b98034f57984a4c35c45b913f30323abc28d99747d6c0c64109efeb37c09`
- Original prepared local commit recovered from prior session context: `0e1296f` (the old checkout itself was unavailable)

The complete preserved checksum inventory is in `NEXUS-U_v2.6_SHA256SUMS.txt`.

## What is original evidence vs reconstructed

- `evidence/ORIGINAL_VALIDATION.md` and `evidence/ORIGINAL_NEXUS_KERNEL.md` preserve the archived release documentation.
- `src/`, `tests/`, `scripts/`, and regenerated `benchmark-results/` are the recovered implementation.
- Recovered outputs deliberately use `NEXUS_KERNEL_VERIFIED_RECOVERED` and a new source digest.

No claim is made that this Git tree or its generated package is byte-identical to the inaccessible archive.
