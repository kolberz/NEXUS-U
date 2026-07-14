from __future__ import annotations

from .ast import App, Case, Const, EmptyElim, EmptyType, Inl, Inr, Lam, Let, Pi, Sort, SumType, Term, Var


def shift(term: Term, delta: int, cutoff: int = 0) -> Term:
    if isinstance(term, Var):
        new_index = term.index + delta if term.index >= cutoff else term.index
        if new_index < 0:
            raise ValueError("invalid negative de Bruijn index after shift")
        return Var(new_index)
    if isinstance(term, (Sort, Const, EmptyType)):
        return term
    if isinstance(term, Pi):
        return Pi(shift(term.domain, delta, cutoff), shift(term.codomain, delta, cutoff + 1))
    if isinstance(term, Lam):
        return Lam(shift(term.domain, delta, cutoff), shift(term.body, delta, cutoff + 1))
    if isinstance(term, App):
        return App(shift(term.function, delta, cutoff), shift(term.argument, delta, cutoff))
    if isinstance(term, Let):
        return Let(
            shift(term.annotation, delta, cutoff),
            shift(term.value, delta, cutoff),
            shift(term.body, delta, cutoff + 1),
        )
    if isinstance(term, SumType):
        return SumType(shift(term.left, delta, cutoff), shift(term.right, delta, cutoff))
    if isinstance(term, Inl):
        return Inl(shift(term.value, delta, cutoff), shift(term.right_type, delta, cutoff))
    if isinstance(term, Inr):
        return Inr(shift(term.left_type, delta, cutoff), shift(term.value, delta, cutoff))
    if isinstance(term, Case):
        return Case(
            shift(term.scrutinee, delta, cutoff),
            shift(term.left_branch, delta, cutoff),
            shift(term.right_branch, delta, cutoff),
            shift(term.result_type, delta, cutoff),
        )
    if isinstance(term, EmptyElim):
        return EmptyElim(shift(term.proof, delta, cutoff), shift(term.result_type, delta, cutoff))
    raise TypeError(f"unsupported term: {type(term).__name__}")


def substitute(term: Term, index: int, replacement: Term, depth: int = 0) -> Term:
    if isinstance(term, Var):
        if term.index == index + depth:
            return shift(replacement, depth)
        return term
    if isinstance(term, (Sort, Const, EmptyType)):
        return term
    if isinstance(term, Pi):
        return Pi(
            substitute(term.domain, index, replacement, depth),
            substitute(term.codomain, index, replacement, depth + 1),
        )
    if isinstance(term, Lam):
        return Lam(
            substitute(term.domain, index, replacement, depth),
            substitute(term.body, index, replacement, depth + 1),
        )
    if isinstance(term, App):
        return App(
            substitute(term.function, index, replacement, depth),
            substitute(term.argument, index, replacement, depth),
        )
    if isinstance(term, Let):
        return Let(
            substitute(term.annotation, index, replacement, depth),
            substitute(term.value, index, replacement, depth),
            substitute(term.body, index, replacement, depth + 1),
        )
    if isinstance(term, SumType):
        return SumType(
            substitute(term.left, index, replacement, depth),
            substitute(term.right, index, replacement, depth),
        )
    if isinstance(term, Inl):
        return Inl(
            substitute(term.value, index, replacement, depth),
            substitute(term.right_type, index, replacement, depth),
        )
    if isinstance(term, Inr):
        return Inr(
            substitute(term.left_type, index, replacement, depth),
            substitute(term.value, index, replacement, depth),
        )
    if isinstance(term, Case):
        return Case(
            substitute(term.scrutinee, index, replacement, depth),
            substitute(term.left_branch, index, replacement, depth),
            substitute(term.right_branch, index, replacement, depth),
            substitute(term.result_type, index, replacement, depth),
        )
    if isinstance(term, EmptyElim):
        return EmptyElim(
            substitute(term.proof, index, replacement, depth),
            substitute(term.result_type, index, replacement, depth),
        )
    raise TypeError(f"unsupported term: {type(term).__name__}")


def substitute_top(replacement: Term, body: Term) -> Term:
    return shift(substitute(body, 0, shift(replacement, 1)), -1)


def node_count(term: Term) -> int:
    if isinstance(term, (Sort, Var, Const, EmptyType)):
        return 1
    if isinstance(term, (Pi, Lam, App, SumType)):
        left = term.domain if isinstance(term, (Pi, Lam)) else term.function if isinstance(term, App) else term.left
        right = term.codomain if isinstance(term, Pi) else term.body if isinstance(term, Lam) else term.argument if isinstance(term, App) else term.right
        return 1 + node_count(left) + node_count(right)
    if isinstance(term, Let):
        return 1 + node_count(term.annotation) + node_count(term.value) + node_count(term.body)
    if isinstance(term, Inl):
        return 1 + node_count(term.value) + node_count(term.right_type)
    if isinstance(term, Inr):
        return 1 + node_count(term.left_type) + node_count(term.value)
    if isinstance(term, Case):
        return 1 + sum(node_count(x) for x in (term.scrutinee, term.left_branch, term.right_branch, term.result_type))
    if isinstance(term, EmptyElim):
        return 1 + node_count(term.proof) + node_count(term.result_type)
    raise TypeError(type(term).__name__)


def max_depth(term: Term) -> int:
    if isinstance(term, (Sort, Var, Const, EmptyType)):
        return 1
    children: tuple[Term, ...]
    if isinstance(term, Pi):
        children = (term.domain, term.codomain)
    elif isinstance(term, Lam):
        children = (term.domain, term.body)
    elif isinstance(term, App):
        children = (term.function, term.argument)
    elif isinstance(term, Let):
        children = (term.annotation, term.value, term.body)
    elif isinstance(term, SumType):
        children = (term.left, term.right)
    elif isinstance(term, Inl):
        children = (term.value, term.right_type)
    elif isinstance(term, Inr):
        children = (term.left_type, term.value)
    elif isinstance(term, Case):
        children = (term.scrutinee, term.left_branch, term.right_branch, term.result_type)
    elif isinstance(term, EmptyElim):
        children = (term.proof, term.result_type)
    else:
        raise TypeError(type(term).__name__)
    return 1 + max(max_depth(child) for child in children)
