from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True, slots=True)
class Sort:
    level: int


@dataclass(frozen=True, slots=True)
class Var:
    index: int


@dataclass(frozen=True, slots=True)
class Const:
    name: str


@dataclass(frozen=True, slots=True)
class Pi:
    domain: "Term"
    codomain: "Term"


@dataclass(frozen=True, slots=True)
class Lam:
    domain: "Term"
    body: "Term"


@dataclass(frozen=True, slots=True)
class App:
    function: "Term"
    argument: "Term"


@dataclass(frozen=True, slots=True)
class Let:
    value_type: "Term"
    value: "Term"
    body: "Term"


@dataclass(frozen=True, slots=True)
class Empty:
    pass


@dataclass(frozen=True, slots=True)
class EmptyElim:
    result_type: "Term"
    proof: "Term"


@dataclass(frozen=True, slots=True)
class Sum:
    left: "Term"
    right: "Term"


@dataclass(frozen=True, slots=True)
class Inl:
    value: "Term"
    right_type: "Term"


@dataclass(frozen=True, slots=True)
class Inr:
    value: "Term"
    left_type: "Term"


@dataclass(frozen=True, slots=True)
class Case:
    scrutinee: "Term"
    left_branch: "Term"
    right_branch: "Term"
    result_type: "Term"


Term: TypeAlias = (
    Sort
    | Var
    | Const
    | Pi
    | Lam
    | App
    | Let
    | Empty
    | EmptyElim
    | Sum
    | Inl
    | Inr
    | Case
)
