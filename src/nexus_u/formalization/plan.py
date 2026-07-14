from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from .models import FormalizationObligation, ObligationStatus


def build_transposition_formalization_plan() -> list[FormalizationObligation]:
    return [
        FormalizationObligation(
            "T0", "Pin the exact published reduction statement and source revision.", "SOURCE",
            status=ObligationStatus.DISCHARGED,
            evidence=["integer-multiplication-challenge.json:harvey_vdh_2025"],
            scope="Metadata identity only; mathematical content still requires encoding.",
        ),
        FormalizationObligation(
            "T1", "Define the offline constant-tape multitape Turing-machine semantics used by both problems.",
            "SEMANTICS", ["T0"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T2", "Define row-major binary matrix encoding, transpose semantics, and size measure.",
            "ENCODING", ["T1"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T3", "Define packed integer encoding and the multiplication interface used by the reduction.",
            "ENCODING", ["T1"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T4", "Encode the published reduction algorithm without changing its machine model.",
            "CONSTRUCTION", ["T2", "T3"], ObligationStatus.EXTERNAL_REQUIRED,
            scope="Requires primary-source recovery and line-by-line formal transcription.",
        ),
        FormalizationObligation(
            "T5", "Prove functional correctness: decoded multiplication output equals matrix transposition.",
            "CORRECTNESS", ["T4"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T6", "Prove the size map and simulation overhead preserve the claimed asymptotic implication.",
            "COMPLEXITY", ["T4"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T7", "Prove model preservation, including tape count, alphabet, head movement, and uniformity.",
            "MODEL", ["T1", "T4"], ObligationStatus.OPEN,
        ),
        FormalizationObligation(
            "T8", "Compose T5-T7 into the conditional lower-bound theorem without discharging the open transposition premise.",
            "COMPOSITION", ["T5", "T6", "T7"], ObligationStatus.OPEN,
            scope="Conclusion remains conditional until the matrix-transposition lower bound is proved.",
        ),
    ]


def verify_plan(plan: Iterable[FormalizationObligation]) -> tuple[bool, list[str], list[str]]:
    items = list(plan)
    errors: list[str] = []
    identifiers = [item.obligation_id for item in items]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Duplicate formalization obligation identifier")
    known = set(identifiers)
    indegree = {item.obligation_id: 0 for item in items}
    outgoing: dict[str, list[str]] = defaultdict(list)
    for item in items:
        for dep in item.dependencies:
            if dep not in known:
                errors.append(f"{item.obligation_id} references missing dependency {dep}")
                continue
            outgoing[dep].append(item.obligation_id)
            indegree[item.obligation_id] += 1
    queue = deque(sorted(key for key, value in indegree.items() if value == 0))
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for nxt in sorted(outgoing[node]):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(order) != len(items):
        errors.append("Formalization obligation graph contains a dependency cycle")
    return not errors, errors, order
