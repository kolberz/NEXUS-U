"""in-toto Statement and SLSA provenance support."""

from .attestation import build_provenance_statement, verify_provenance_statement

__all__ = ["build_provenance_statement", "verify_provenance_statement"]
