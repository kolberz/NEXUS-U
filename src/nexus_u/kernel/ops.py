from __future__ import annotations

from dataclasses import fields, is_dataclass

from .ast import (
    App,
    Case,
    Const,
    Empty,
    EmptyElim,
    Inl,
    Inr,
    Lam,
    Let,
    Pi,
    Sort,
    Sum,
    Term,
    Var,
)


class TermOperationError(ValueError):
    pass


def shift(term: Term, delta: int, cutoff: int = 0) -> Term:
    """Shift free de Bruijn indices by ``delta`` above ``cutoff``."""
    match term:
        case Sort() | Const() | Empty():
            return term
        case Var(index=i):
            if i < cutoff:
                return term
            shifted = i + delta
            if shifted < 0:
                raise TermOperationError("negative de Bruijn index")
            return Var(shifted)
        case Pi(domain=a, codomain=b):
            return Pi(shift(a, delta, cutoff), shift(b, delta, cutoff + 1))
        case Lam(domain=a, body=b):
            return Lam(shift(a, delta, cutoff), shift(b, delta, cutoff + 1))
        case App(function=f, argument=a):
            return App(shift(f, delta, cutoff), shift(a, delta, cutoff))
        case Let(value_type=t, value=v, body=b):
            return Let(
                shift(t, delta, cutoff),
                shift(v, delta, cutoff),
                shift(b, delta, cutoff + 1),
            )
        case EmptyElim(result_type=t, proof=p):
            return EmptyElim(shift(t, delta, cutoff), shift(p, delta, cutoff))
        case Sum(left=a, right=b):
            return Sum(shift(a, delta, cutoff), shift(b, delta, cutoff))
        case Inl(value=v, right_type=t):
            return Inl(shift(v, delta, cutoff), shift(t, delta, cutoff))
        case Inr(value=v, left_type=t):
            return Inr(shift(v, delta, cutoff), shift(t, delta, cutoff))
        case Case(scrutinee=s, left_branch=l, right_branch=r, result_type=t):
            return Case(
                shift(s, delta, cutoff),
                shift(l, delta, cutoff),
                shift(r, delta, cutoff),
                shift(t, delta, cutoff),
            )
        case _:
            raise TermOperationError(f"unsupported term: {type(term).__name__}")


def substitute(term: Term, index: int, replacement: Term, cutoff: int = 0) -> Term:
    """Replace variable ``index`` with a term, respecting binders."""
    match term:
        case Sort() | Const() | Empty():
            return term
        case Var(index=i):
            target = index + cutoff
            if i == target:
                return shift(replacement, cutoff)
            return term
        case Pi(domain=a, codomain=b):
            return Pi(
                substitute(a, index, replacement, cutoff),
                substitute(b, index, replacement, cutoff + 1),
            )
        case Lam(domain=a, body=b):
            return Lam(
                substitute(a, index, replacement, cutoff),
                substitute(b, index, replacement, cutoff + 1),
            )
        case App(function=f, argument=a):
            return App(
                substitute(f, index, replacement, cutoff),
                substitute(a, index, replacement, cutoff),
            )
        case Let(value_type=t, value=v, body=b):
            return Let(
                substitute(t, index, replacement, cutoff),
                substitute(v, index, replacement, cutoff),
                substitute(b, index, replacement, cutoff + 1),
            )
        case EmptyElim(result_type=t, proof=p):
            return EmptyElim(
                substitute(t, index, replacement, cutoff),
                substitute(p, index, replacement, cutoff),
            )
        case Sum(left=a, right=b):
            return Sum(
                substitute(a, index, replacement, cutoff),
                substitute(b, index, replacement, cutoff),
            )
        case Inl(value=v, right_type=t):
            return Inl(
                substitute(v, index, replacement, cutoff),
                substitute(t, index, replacement, cutoff),
            )
        case Inr(value=v, left_type=t):
            return Inr(
                substitute(v, index, replacement, cutoff),
                substitute(t, index, replacement, cutoff),
            )
        case Case(scrutinee=s, left_branch=l, right_branch=r, result_type=t):
            return Case(
                substitute(s, index, replacement, cutoff),
                substitute(l, index, replacement, cutoff),
                substitute(r, index, replacement, cutoff),
                substitute(t, index, replacement, cutoff),
            )
        case _:
            raise TermOperationError(f"unsupported term: {type(term).__name__}")


def substitute_top(body: Term, value: Term) -> Term:
    return shift(substitute(body, 0, shift(value, 1)), -1)


def term_size(term: Term) -> int:
    total = 1
    for field in fields(term) if is_dataclass(term) else ():
        value = getattr(term, field.name)
        if is_dataclass(value):
            total += term_size(value)
    return total


def term_depth(term: Term) -> int:
    child_depths = []
    for field in fields(term) if is_dataclass(term) else ():
        value = getattr(term, field.name)
        if is_dataclass(value):
            child_depths.append(term_depth(value))
    return 1 + max(child_depths, default=0)
