# NEXUS-U 2.6 Recovery Validation

## Preserved release facts

The archived v2.6 report recorded 111 passing tests, 11 native-kernel-focused tests, Python compilation success, and a 17/17 native-kernel benchmark. It explicitly stated that the kernel was not Lean-compatible and that the universal offline integer-multiplication lower bound remained open.

## Recovery validation

This repository independently regenerates a 17-check native-kernel benchmark from reconstructed source. It preserves the same scope boundaries but uses a distinct recovery status and source digest.

Run:

```bash
python -m pip install -e .
pytest
nexus-u nexus-kernel-benchmark --output benchmark-results
nexus-u kernel-check benchmark-results/nexus-kernel-proof.json
```

The repository must not be represented as byte-identical to the archived ZIP unless the original archive is later recovered and its SHA-256 matches the inventory.
