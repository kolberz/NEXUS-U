from __future__ import annotations

from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
from typing import Sequence

from .ast import App, Case, Const, EMPTY, EmptyElim, EmptyType, Inl, Inr, Lam, Let, Pi, Sort, SumType, Term, Var
from .environment import Declaration, Environment
from .ops import max_depth, node_count, shift, substitute_top


class KernelError(ValueError):
    pass


class TypeCheckError(KernelError):
    pass


class ReductionLimitError(KernelError):
    pass


@dataclass(frozen=True, slots=True)
class KernelLimits:
    max_nodes: int = 100_000
    max_depth: int = 2_000
    max_reductions: int = 250_000
    max_universe: int = 1_024


@dataclass(slots=True)
class _Budget:
    reductions: int = 0


class NexusKernel:
    """A small predicative dependent-type kernel.

    Trusted rules:
      * universes (`Sort u : Sort (u+1)`),
      * dependent function formation/introduction/elimination,
      * local definitions,
      * binary sum formation/introduction/non-dependent elimination,
      * the empty type and its eliminator,
      * beta, delta, zeta, and sum-case reduction.

    The kernel uses nameless de Bruijn terms. Parsers, pretty-printers, theorem
    generators, automation, and search are outside the trusted proof rules.
    """

    version = "nexus-kernel-v0.1.0"

    def __init__(self, environment: Environment | None = None, *, limits: KernelLimits | None = None) -> None:
        self.environment = environment or Environment()
        self.limits = limits or KernelLimits()

    @classmethod
    def source_digest(cls) -> str:
        modules = [Path(inspect.getsourcefile(cls) or ""), Path(__file__).with_name("ast.py"), Path(__file__).with_name("ops.py"), Path(__file__).with_name("environment.py")]
        digest = hashlib.sha256()
        for path in sorted(modules):
            digest.update(path.name.encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _guard(self, term: Term) -> None:
        count = node_count(term)
        depth = max_depth(term)
        if count > self.limits.max_nodes:
            raise KernelError(f"term exceeds node limit: {count} > {self.limits.max_nodes}")
        if depth > self.limits.max_depth:
            raise KernelError(f"term exceeds depth limit: {depth} > {self.limits.max_depth}")

    def _step(self, budget: _Budget) -> None:
        budget.reductions += 1
        if budget.reductions > self.limits.max_reductions:
            raise ReductionLimitError("normalization reduction limit exceeded")

    def whnf(self, term: Term, *, budget: _Budget | None = None) -> Term:
        work = budget or _Budget()
        current = term
        while True:
            if isinstance(current, Const):
                declaration = self.environment.get(current.name)
                if declaration.value is not None and not declaration.opaque:
                    self._step(work)
                    current = declaration.value
                    continue
                return current
            if isinstance(current, App):
                fn = self.whnf(current.function, budget=work)
                if isinstance(fn, Lam):
                    self._step(work)
                    current = substitute_top(current.argument, fn.body)
                    continue
                return App(fn, current.argument)
            if isinstance(current, Let):
                self._step(work)
                current = substitute_top(current.value, current.body)
                continue
            if isinstance(current, Case):
                scrutinee = self.whnf(current.scrutinee, budget=work)
                if isinstance(scrutinee, Inl):
                    self._step(work)
                    current = App(current.left_branch, scrutinee.value)
                    continue
                if isinstance(scrutinee, Inr):
                    self._step(work)
                    current = App(current.right_branch, scrutinee.value)
                    continue
                return Case(scrutinee, current.left_branch, current.right_branch, current.result_type)
            return current

    def normalize(self, term: Term, *, budget: _Budget | None = None) -> Term:
        work = budget or _Budget()
        head = self.whnf(term, budget=work)
        if isinstance(head, (Sort, Var, Const, EmptyType)):
            return head
        if isinstance(head, Pi):
            return Pi(self.normalize(head.domain, budget=work), self.normalize(head.codomain, budget=work))
        if isinstance(head, Lam):
            return Lam(self.normalize(head.domain, budget=work), self.normalize(head.body, budget=work))
        if isinstance(head, App):
            return App(self.normalize(head.function, budget=work), self.normalize(head.argument, budget=work))
        if isinstance(head, Let):
            return self.normalize(self.whnf(head, budget=work), budget=work)
        if isinstance(head, SumType):
            return SumType(self.normalize(head.left, budget=work), self.normalize(head.right, budget=work))
        if isinstance(head, Inl):
            return Inl(self.normalize(head.value, budget=work), self.normalize(head.right_type, budget=work))
        if isinstance(head, Inr):
            return Inr(self.normalize(head.left_type, budget=work), self.normalize(head.value, budget=work))
        if isinstance(head, Case):
            return Case(
                self.normalize(head.scrutinee, budget=work),
                self.normalize(head.left_branch, budget=work),
                self.normalize(head.right_branch, budget=work),
                self.normalize(head.result_type, budget=work),
            )
        if isinstance(head, EmptyElim):
            return EmptyElim(self.normalize(head.proof, budget=work), self.normalize(head.result_type, budget=work))
        raise TypeError(type(head).__name__)

    def convertible(self, left: Term, right: Term) -> bool:
        self._guard(left)
        self._guard(right)
        budget = _Budget()
        return self.normalize(left, budget=budget) == self.normalize(right, budget=budget)

    @staticmethod
    def _context_lookup(context: Sequence[Term], index: int) -> Term:
        if index >= len(context):
            raise TypeCheckError(f"unbound variable index {index}")
        return shift(context[index], index + 1)

    def _expect_sort(self, term: Term, context: Sequence[Term], budget: _Budget) -> int:
        inferred = self.whnf(self._infer(term, context, budget), budget=budget)
        if not isinstance(inferred, Sort):
            raise TypeCheckError(f"expected a type, inferred {inferred!r}")
        if inferred.level > self.limits.max_universe:
            raise TypeCheckError("universe limit exceeded")
        return inferred.level

    def infer(self, term: Term, context: Sequence[Term] = ()) -> Term:
        self._guard(term)
        return self._infer(term, tuple(context), _Budget())

    def _infer(self, term: Term, context: Sequence[Term], budget: _Budget) -> Term:
        if isinstance(term, Sort):
            if term.level >= self.limits.max_universe:
                raise TypeCheckError("universe limit exceeded")
            return Sort(term.level + 1)
        if isinstance(term, Var):
            return self._context_lookup(context, term.index)
        if isinstance(term, Const):
            return self.environment.get(term.name).type
        if isinstance(term, Pi):
            domain_level = self._expect_sort(term.domain, context, budget)
            codomain_level = self._expect_sort(term.codomain, (term.domain, *context), budget)
            return Sort(max(domain_level, codomain_level))
        if isinstance(term, Lam):
            self._expect_sort(term.domain, context, budget)
            body_type = self._infer(term.body, (term.domain, *context), budget)
            return Pi(term.domain, body_type)
        if isinstance(term, App):
            function_type = self.whnf(self._infer(term.function, context, budget), budget=budget)
            if not isinstance(function_type, Pi):
                raise TypeCheckError("application target does not have a dependent function type")
            self.check(term.argument, function_type.domain, context=context, _budget=budget)
            return substitute_top(term.argument, function_type.codomain)
        if isinstance(term, Let):
            self._expect_sort(term.annotation, context, budget)
            self.check(term.value, term.annotation, context=context, _budget=budget)
            body_type = self._infer(term.body, (term.annotation, *context), budget)
            return substitute_top(term.value, body_type)
        if isinstance(term, SumType):
            left_level = self._expect_sort(term.left, context, budget)
            right_level = self._expect_sort(term.right, context, budget)
            return Sort(max(left_level, right_level))
        if isinstance(term, Inl):
            value_type = self._infer(term.value, context, budget)
            self._expect_sort(term.right_type, context, budget)
            return SumType(value_type, term.right_type)
        if isinstance(term, Inr):
            self._expect_sort(term.left_type, context, budget)
            value_type = self._infer(term.value, context, budget)
            return SumType(term.left_type, value_type)
        if isinstance(term, Case):
            sum_type = self.whnf(self._infer(term.scrutinee, context, budget), budget=budget)
            if not isinstance(sum_type, SumType):
                raise TypeCheckError("case scrutinee is not a sum")
            self._expect_sort(term.result_type, context, budget)
            left_expected = Pi(sum_type.left, shift(term.result_type, 1))
            right_expected = Pi(sum_type.right, shift(term.result_type, 1))
            self.check(term.left_branch, left_expected, context=context, _budget=budget)
            self.check(term.right_branch, right_expected, context=context, _budget=budget)
            return term.result_type
        if isinstance(term, EmptyType):
            return Sort(0)
        if isinstance(term, EmptyElim):
            self.check(term.proof, EMPTY, context=context, _budget=budget)
            self._expect_sort(term.result_type, context, budget)
            return term.result_type
        raise TypeCheckError(f"unsupported term: {type(term).__name__}")

    def check(self, term: Term, expected: Term, context: Sequence[Term] = (), *, _budget: _Budget | None = None) -> None:
        self._guard(term)
        self._guard(expected)
        budget = _budget or _Budget()
        inferred = self._infer(term, tuple(context), budget)
        if not self._convertible_with_budget(inferred, expected, budget):
            raise TypeCheckError(f"type mismatch\n  inferred: {inferred!r}\n  expected: {expected!r}")

    def _convertible_with_budget(self, left: Term, right: Term, budget: _Budget) -> bool:
        return self.normalize(left, budget=budget) == self.normalize(right, budget=budget)

    def declare_axiom(self, name: str, type_term: Term) -> Declaration:
        self._expect_sort(type_term, (), _Budget())
        declaration = Declaration(name=name, type=type_term)
        self.environment.add_unchecked(declaration)
        return declaration

    def declare_definition(self, name: str, type_term: Term, value: Term, *, opaque: bool = False) -> Declaration:
        self._expect_sort(type_term, (), _Budget())
        self.check(value, type_term)
        declaration = Declaration(name=name, type=type_term, value=value, opaque=opaque)
        self.environment.add_unchecked(declaration)
        return declaration

    def verify(self, proof: Term, theorem: Term) -> dict[str, object]:
        self._expect_sort(theorem, (), _Budget())
        self.check(proof, theorem)
        return {
            "kernel": self.version,
            "kernel_sha256": self.source_digest(),
            "valid": True,
            "proof_nodes": node_count(proof),
            "proof_depth": max_depth(proof),
            "theorem_nodes": node_count(theorem),
            "axioms": list(self.environment.axioms()),
        }
