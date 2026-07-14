from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Union

from .ast import App, Case, EMPTY, EmptyElim, Inl, Inr, Lam, Let, Pi, Sort, SumType, Term, Var


@dataclass(frozen=True, slots=True)
class SVar:
    name: str


@dataclass(frozen=True, slots=True)
class SSort:
    level: int


@dataclass(frozen=True, slots=True)
class SPi:
    name: str
    domain: "SurfaceTerm"
    codomain: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SLam:
    name: str
    domain: "SurfaceTerm"
    body: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SApp:
    function: "SurfaceTerm"
    argument: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SLet:
    name: str
    annotation: "SurfaceTerm"
    value: "SurfaceTerm"
    body: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SSum:
    left: "SurfaceTerm"
    right: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SInl:
    value: "SurfaceTerm"
    right_type: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SInr:
    left_type: "SurfaceTerm"
    value: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SCase:
    scrutinee: "SurfaceTerm"
    left_branch: "SurfaceTerm"
    right_branch: "SurfaceTerm"
    result_type: "SurfaceTerm"


@dataclass(frozen=True, slots=True)
class SEmpty:
    pass


@dataclass(frozen=True, slots=True)
class SEmptyElim:
    proof: "SurfaceTerm"
    result_type: "SurfaceTerm"


SurfaceTerm: TypeAlias = Union[SVar, SSort, SPi, SLam, SApp, SLet, SSum, SInl, SInr, SCase, SEmpty, SEmptyElim]


def elaborate(term: SurfaceTerm, context: tuple[str, ...] = ()) -> Term:
    if isinstance(term, SVar):
        try:
            return Var(context.index(term.name))
        except ValueError as exc:
            raise ValueError(f"unbound surface variable: {term.name}") from exc
    if isinstance(term, SSort):
        return Sort(term.level)
    if isinstance(term, SPi):
        if term.name in context:
            raise ValueError(f"surface binder shadows an existing name: {term.name}")
        return Pi(elaborate(term.domain, context), elaborate(term.codomain, (term.name, *context)))
    if isinstance(term, SLam):
        if term.name in context:
            raise ValueError(f"surface binder shadows an existing name: {term.name}")
        return Lam(elaborate(term.domain, context), elaborate(term.body, (term.name, *context)))
    if isinstance(term, SApp):
        return App(elaborate(term.function, context), elaborate(term.argument, context))
    if isinstance(term, SLet):
        if term.name in context:
            raise ValueError(f"surface binder shadows an existing name: {term.name}")
        return Let(elaborate(term.annotation, context), elaborate(term.value, context), elaborate(term.body, (term.name, *context)))
    if isinstance(term, SSum):
        return SumType(elaborate(term.left, context), elaborate(term.right, context))
    if isinstance(term, SInl):
        return Inl(elaborate(term.value, context), elaborate(term.right_type, context))
    if isinstance(term, SInr):
        return Inr(elaborate(term.left_type, context), elaborate(term.value, context))
    if isinstance(term, SCase):
        return Case(
            elaborate(term.scrutinee, context),
            elaborate(term.left_branch, context),
            elaborate(term.right_branch, context),
            elaborate(term.result_type, context),
        )
    if isinstance(term, SEmpty):
        return EMPTY
    if isinstance(term, SEmptyElim):
        return EmptyElim(elaborate(term.proof, context), elaborate(term.result_type, context))
    raise TypeError(type(term).__name__)
