from __future__ import annotations

from dataclasses import dataclass

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
from .environment import Environment, EnvironmentError
from .ops import shift, substitute_top, term_depth, term_size


class KernelError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class KernelLimits:
    max_nodes: int = 50_000
    max_depth: int = 512
    max_reduction_steps: int = 100_000
    max_universe: int = 64


class Kernel:
    def __init__(self, environment: Environment | None = None, limits: KernelLimits | None = None):
        self.environment = environment or Environment()
        self.limits = limits or KernelLimits()
        self._steps = 0

    def _tick(self) -> None:
        self._steps += 1
        if self._steps > self.limits.max_reduction_steps:
            raise KernelError("reduction step limit exceeded")

    def _validate_resource_bounds(self, term: Term) -> None:
        if term_size(term) > self.limits.max_nodes:
            raise KernelError("term node limit exceeded")
        if term_depth(term) > self.limits.max_depth:
            raise KernelError("term depth limit exceeded")

    def _lookup_context(self, context: tuple[Term, ...], index: int) -> Term:
        if index < 0 or index >= len(context):
            raise KernelError(f"unbound variable: {index}")
        return shift(context[index], index + 1)

    def infer(self, term: Term, context: tuple[Term, ...] = ()) -> Term:
        self._validate_resource_bounds(term)
        match term:
            case Sort(level=level):
                if level < 0 or level > self.limits.max_universe:
                    raise KernelError("invalid universe level")
                if level == self.limits.max_universe:
                    raise KernelError("universe successor exceeds configured limit")
                return Sort(level + 1)
            case Var(index=index):
                return self._lookup_context(context, index)
            case Const(name=name):
                try:
                    return self.environment.lookup(name).type
                except EnvironmentError as exc:
                    raise KernelError(str(exc)) from exc
            case Empty():
                return Sort(0)
            case Pi(domain=domain, codomain=codomain):
                domain_sort = self._expect_sort(self.infer(domain, context))
                codomain_sort = self._expect_sort(self.infer(codomain, (domain,) + context))
                return Sort(max(domain_sort, codomain_sort))
            case Lam(domain=domain, body=body):
                self._expect_sort(self.infer(domain, context))
                body_type = self.infer(body, (domain,) + context)
                return Pi(domain, body_type)
            case App(function=function, argument=argument):
                function_type = self.normalize(self.infer(function, context))
                if not isinstance(function_type, Pi):
                    raise KernelError("application target is not a function")
                self.check(argument, function_type.domain, context)
                return substitute_top(function_type.codomain, argument)
            case Let(value_type=value_type, value=value, body=body):
                self._expect_sort(self.infer(value_type, context))
                self.check(value, value_type, context)
                body_type = self.infer(body, (value_type,) + context)
                return substitute_top(body_type, value)
            case EmptyElim(result_type=result_type, proof=proof):
                self._expect_sort(self.infer(result_type, context))
                self.check(proof, Empty(), context)
                return result_type
            case Sum(left=left, right=right):
                left_sort = self._expect_sort(self.infer(left, context))
                right_sort = self._expect_sort(self.infer(right, context))
                return Sort(max(left_sort, right_sort))
            case Inl(value=value, right_type=right_type):
                self._expect_sort(self.infer(right_type, context))
                return Sum(self.infer(value, context), right_type)
            case Inr(value=value, left_type=left_type):
                self._expect_sort(self.infer(left_type, context))
                return Sum(left_type, self.infer(value, context))
            case Case(scrutinee=scrutinee, left_branch=left_branch, right_branch=right_branch, result_type=result_type):
                self._expect_sort(self.infer(result_type, context))
                scrutinee_type = self.normalize(self.infer(scrutinee, context))
                if not isinstance(scrutinee_type, Sum):
                    raise KernelError("case scrutinee is not a sum")
                left_expected = Pi(scrutinee_type.left, shift(result_type, 1))
                right_expected = Pi(scrutinee_type.right, shift(result_type, 1))
                self.check(left_branch, left_expected, context)
                self.check(right_branch, right_expected, context)
                return result_type
            case _:
                raise KernelError(f"unsupported term: {type(term).__name__}")

    def _expect_sort(self, term: Term) -> int:
        normalized = self.normalize(term)
        if not isinstance(normalized, Sort):
            raise KernelError("expected a type")
        return normalized.level

    def check(self, term: Term, expected: Term, context: tuple[Term, ...] = ()) -> None:
        inferred = self.infer(term, context)
        if not self.definitionally_equal(inferred, expected):
            raise KernelError(
                f"type mismatch: inferred {inferred!r}, expected {expected!r}"
            )

    def normalize(self, term: Term) -> Term:
        self._steps = 0
        self._validate_resource_bounds(term)
        return self._normalize(term)

    def _normalize(self, term: Term) -> Term:
        self._tick()
        match term:
            case Sort() | Var() | Empty():
                return term
            case Const(name=name):
                try:
                    declaration = self.environment.lookup(name)
                except EnvironmentError as exc:
                    raise KernelError(str(exc)) from exc
                if declaration.value is not None and not declaration.opaque:
                    return self._normalize(declaration.value)
                return term
            case Pi(domain=domain, codomain=codomain):
                return Pi(self._normalize(domain), self._normalize(codomain))
            case Lam(domain=domain, body=body):
                return Lam(self._normalize(domain), self._normalize(body))
            case App(function=function, argument=argument):
                normalized_function = self._normalize(function)
                normalized_argument = self._normalize(argument)
                if isinstance(normalized_function, Lam):
                    return self._normalize(
                        substitute_top(normalized_function.body, normalized_argument)
                    )
                return App(normalized_function, normalized_argument)
            case Let(value_type=value_type, value=value, body=body):
                normalized_value = self._normalize(value)
                return self._normalize(substitute_top(body, normalized_value))
            case EmptyElim(result_type=result_type, proof=proof):
                return EmptyElim(self._normalize(result_type), self._normalize(proof))
            case Sum(left=left, right=right):
                return Sum(self._normalize(left), self._normalize(right))
            case Inl(value=value, right_type=right_type):
                return Inl(self._normalize(value), self._normalize(right_type))
            case Inr(value=value, left_type=left_type):
                return Inr(self._normalize(value), self._normalize(left_type))
            case Case(scrutinee=scrutinee, left_branch=left_branch, right_branch=right_branch, result_type=result_type):
                normalized_scrutinee = self._normalize(scrutinee)
                normalized_left = self._normalize(left_branch)
                normalized_right = self._normalize(right_branch)
                if isinstance(normalized_scrutinee, Inl):
                    return self._normalize(App(normalized_left, normalized_scrutinee.value))
                if isinstance(normalized_scrutinee, Inr):
                    return self._normalize(App(normalized_right, normalized_scrutinee.value))
                return Case(
                    normalized_scrutinee,
                    normalized_left,
                    normalized_right,
                    self._normalize(result_type),
                )
            case _:
                raise KernelError(f"unsupported term: {type(term).__name__}")

    def definitionally_equal(self, left: Term, right: Term) -> bool:
        return self.normalize(left) == self.normalize(right)

    def add_definition(self, name: str, type_: Term, value: Term, *, opaque: bool = False) -> None:
        self._expect_sort(self.infer(type_))
        self.check(value, type_)
        self.environment.add_definition(name, type_, value, opaque=opaque)
