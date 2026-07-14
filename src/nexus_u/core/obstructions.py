from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ObstructionCode(StrEnum):
    FALSE = "O-FALSE"
    PREMISE = "O-PREMISE"
    SHAPE = "O-SHAPE"
    REPRESENTATION = "O-REPRESENTATION"
    MISSING_LEMMA = "O-MISSING-LEMMA"
    LIBRARY = "O-LIBRARY"
    TYPE = "O-TYPE"
    ALGORITHM = "O-ALGORITHM"
    IMPLEMENTATION = "O-IMPLEMENTATION"
    TEST = "O-TEST"
    ENVIRONMENT = "O-ENVIRONMENT"
    MODEL = "O-MODEL"
    DATA = "O-DATA"
    SAFETY = "O-SAFETY"
    RISK = "O-RISK"
    RESOURCE = "O-RESOURCE"
    NUMERIC = "O-NUMERIC"
    CAUSAL = "O-CAUSAL"
    COMPLIANCE = "O-COMPLIANCE"
    EVIDENCE = "O-EVIDENCE"
    DRIFT = "O-DRIFT"
    CIRCULARITY = "O-CIRCULARITY"
    BUDGET = "O-BUDGET"
    UNKNOWN = "O-UNKNOWN"


@dataclass(frozen=True, slots=True)
class Obstruction:
    code: ObstructionCode
    summary: str
    evidence: tuple[str, ...] = ()


ROUTES: dict[ObstructionCode, tuple[str, ...]] = {
    ObstructionCode.FALSE: ("REJECT_AND_ARCHIVE_COUNTEREXAMPLE",),
    ObstructionCode.PREMISE: ("EXPOSE_ASSUMPTION", "NARROW_SCOPE"),
    ObstructionCode.SHAPE: ("SEARCH_ARTIFACT_SHAPE",),
    ObstructionCode.REPRESENTATION: ("ADD_TRANSPORT_LAYER",),
    ObstructionCode.MISSING_LEMMA: ("GENERATE_LOAD_BEARING_SUBARTIFACT",),
    ObstructionCode.LIBRARY: ("SEARCH_REUSABLE_COMPONENTS",),
    ObstructionCode.TYPE: ("REPAIR_SCHEMA_OR_INTERFACE",),
    ObstructionCode.ALGORITHM: ("SWITCH_ALGORITHM", "DECOMPOSE"),
    ObstructionCode.IMPLEMENTATION: ("LOCAL_REPAIR",),
    ObstructionCode.TEST: ("REPAIR_BEHAVIOR", "REVIEW_TEST_ORACLE"),
    ObstructionCode.ENVIRONMENT: ("REPAIR_ENVIRONMENT",),
    ObstructionCode.MODEL: ("REFIT_OR_REPLACE_MODEL",),
    ObstructionCode.DATA: ("CORRECT_EXPAND_OR_REJECT_DATA",),
    ObstructionCode.SAFETY: ("SHIELD_CONSTRAIN_OR_HALT",),
    ObstructionCode.RISK: ("RETYPE_RISK_AND_REESTIMATE",),
    ObstructionCode.RESOURCE: ("LOWER_COMPRESS_DEGRADE_OR_REJECT",),
    ObstructionCode.NUMERIC: ("BOUND_ERROR_AND_RECOMPUTE",),
    ObstructionCode.CAUSAL: ("REBUILD_CAUSAL_MODEL",),
    ObstructionCode.COMPLIANCE: ("ESCALATE_POLICY_REVIEW",),
    ObstructionCode.EVIDENCE: ("LOWER_CLAIM_STATUS",),
    ObstructionCode.DRIFT: ("REJECT_TRANSFORMATION",),
    ObstructionCode.CIRCULARITY: ("REJECT_CONSTRUCTION",),
    ObstructionCode.BUDGET: ("DECOMPOSE_SHELF_OR_ESCALATE",),
    ObstructionCode.UNKNOWN: ("COLLECT_MORE_EVIDENCE",),
}


def route(obstruction: Obstruction) -> tuple[str, ...]:
    return ROUTES[obstruction.code]
