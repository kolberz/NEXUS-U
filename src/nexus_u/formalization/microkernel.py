from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Union


@dataclass(frozen=True, slots=True)
class Atom:
    name: str


@dataclass(frozen=True, slots=True)
class Bottom:
    pass


@dataclass(frozen=True, slots=True)
class Imp:
    left: "Formula"
    right: "Formula"


@dataclass(frozen=True, slots=True)
class And:
    left: "Formula"
    right: "Formula"


Formula = Union[Atom, Bottom, Imp, And]
BOTTOM = Bottom()


def Not(formula: Formula) -> Formula:
    return Imp(formula, BOTTOM)


@dataclass(frozen=True, slots=True)
class Hyp:
    name: str


@dataclass(frozen=True, slots=True)
class Lam:
    name: str
    assumption: Formula
    body: "Term"


@dataclass(frozen=True, slots=True)
class App:
    function: "Term"
    argument: "Term"


@dataclass(frozen=True, slots=True)
class Pair:
    left: "Term"
    right: "Term"


@dataclass(frozen=True, slots=True)
class Fst:
    pair: "Term"


@dataclass(frozen=True, slots=True)
class Snd:
    pair: "Term"


@dataclass(frozen=True, slots=True)
class Dne:
    formula: Formula
    proof: "Term"


Term = Union[Hyp, Lam, App, Pair, Fst, Snd, Dne]


class ProofError(ValueError):
    pass


class NaturalDeductionMicrokernel:
    """Tiny proof-term checker for propositional natural deduction.

    DNE is permitted only for formulas explicitly declared decidable. This models
    the decision-tree theorem's queried-bit proposition, which is a Boolean equality.
    The checker is independent of the multiplication-specific arithmetic certificate.
    """

    version = "nexus-nd-microkernel-v1"

    @classmethod
    def digest(cls) -> str:
        import inspect
        return hashlib.sha256(inspect.getsource(cls).encode("utf-8")).hexdigest()

    @classmethod
    def infer(
        cls,
        term: Term,
        context: Mapping[str, Formula] | None = None,
        *,
        decidable: frozenset[Formula] = frozenset(),
    ) -> Formula:
        ctx = dict(context or {})
        if isinstance(term, Hyp):
            if term.name not in ctx:
                raise ProofError(f"unknown hypothesis: {term.name}")
            return ctx[term.name]
        if isinstance(term, Lam):
            if term.name in ctx:
                raise ProofError(f"shadowed hypothesis: {term.name}")
            extended = dict(ctx)
            extended[term.name] = term.assumption
            return Imp(term.assumption, cls.infer(term.body, extended, decidable=decidable))
        if isinstance(term, App):
            fn_type = cls.infer(term.function, ctx, decidable=decidable)
            arg_type = cls.infer(term.argument, ctx, decidable=decidable)
            if not isinstance(fn_type, Imp):
                raise ProofError("application target is not an implication")
            if fn_type.left != arg_type:
                raise ProofError("application argument type mismatch")
            return fn_type.right
        if isinstance(term, Pair):
            return And(
                cls.infer(term.left, ctx, decidable=decidable),
                cls.infer(term.right, ctx, decidable=decidable),
            )
        if isinstance(term, Fst):
            pair_type = cls.infer(term.pair, ctx, decidable=decidable)
            if not isinstance(pair_type, And):
                raise ProofError("fst target is not a conjunction")
            return pair_type.left
        if isinstance(term, Snd):
            pair_type = cls.infer(term.pair, ctx, decidable=decidable)
            if not isinstance(pair_type, And):
                raise ProofError("snd target is not a conjunction")
            return pair_type.right
        if isinstance(term, Dne):
            if term.formula not in decidable:
                raise ProofError("DNE requested for a formula not declared decidable")
            proof_type = cls.infer(term.proof, ctx, decidable=decidable)
            if proof_type != Not(Not(term.formula)):
                raise ProofError("DNE requires a proof of double negation")
            return term.formula
        raise ProofError(f"unsupported proof term: {type(term).__name__}")


def decision_tree_schema() -> tuple[Formula, Term, frozenset[Formula]]:
    """Return the checked logical core of the sensitivity-to-query argument."""
    queried = Atom("queried")
    same_transcript = Atom("same_transcript")
    equal_output = Atom("equal_output")
    sensitivity = And(same_transcript, Not(equal_output))
    preserve = Imp(Not(queried), same_transcript)
    path_exact = Imp(same_transcript, equal_output)
    theorem = Imp(sensitivity, Imp(preserve, Imp(path_exact, queried)))

    contradiction = App(
        Snd(Hyp("sensitivity")),
        App(Hyp("path_exact"), App(Hyp("preserve"), Hyp("not_queried"))),
    )
    proof = Lam(
        "sensitivity",
        sensitivity,
        Lam(
            "preserve",
            preserve,
            Lam(
                "path_exact",
                path_exact,
                Dne(queried, Lam("not_queried", Not(queried), contradiction)),
            ),
        ),
    )
    return theorem, proof, frozenset({queried})


def verify_decision_tree_schema() -> dict[str, object]:
    theorem, proof, decidable = decision_tree_schema()
    inferred = NaturalDeductionMicrokernel.infer(proof, decidable=decidable)
    valid = inferred == theorem
    payload = {
        "schema": "https://nexus-u.dev/natural-deduction-certificate/v1",
        "kernel": NaturalDeductionMicrokernel.version,
        "kernel_sha256": NaturalDeductionMicrokernel.digest(),
        "theorem": repr(theorem),
        "inferred": repr(inferred),
        "valid": valid,
        "scope": "propositional logical core of sensitivity-to-query path argument",
        "external_proof_assistant": False,
    }
    payload["certificate_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def mutation_suite() -> dict[str, bool]:
    theorem, proof, decidable = decision_tree_schema()
    queried = Atom("queried")
    same = Atom("same_transcript")
    eq = Atom("equal_output")
    sensitivity = And(same, Not(eq))
    preserve = Imp(Not(queried), same)
    path_exact = Imp(same, eq)

    mutations: dict[str, tuple[Term, frozenset[Formula]]] = {
        "reject_missing_sensitivity_negation": (
            Lam("sensitivity", And(same, eq), Lam("preserve", preserve, Lam("path_exact", path_exact, Hyp("queried")))),
            decidable,
        ),
        "reject_wrong_path_direction": (
            Lam("sensitivity", sensitivity, Lam("preserve", preserve, Lam("path_exact", Imp(eq, same), proof))),
            decidable,
        ),
        "reject_unbound_hypothesis": (Hyp("fabricated"), decidable),
        "reject_unlicensed_dne": (proof, frozenset()),
        "reject_argument_mismatch": (App(Hyp("f"), Hyp("x")), decidable),
    }
    results: dict[str, bool] = {}
    for name, (candidate, allowed) in mutations.items():
        try:
            inferred = NaturalDeductionMicrokernel.infer(candidate, decidable=allowed)
            results[name] = inferred != theorem
        except ProofError:
            results[name] = True
    return results
