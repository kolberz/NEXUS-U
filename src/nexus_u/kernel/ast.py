from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias, Union


@dataclass(frozen=True, slots=True)
class Sort:
    level: int

    def __post_init__(self) -> None:
        if self.level < 0:
            raise ValueError("universe levels must be non-negative")


@dataclass(frozen=True, slots=True)
class Var:
    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("de Bruijn indices must be non-negative")


@dataclass(frozen=True, slots=True)
class Const:
    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("constant names must be non-empty")


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
    annotation: "Term"
    value: "Term"
    body: "Term"


@dataclass(frozen=True, slots=True)
class SumType:
    left: "Term"
    right: "Term"


@dataclass(frozen=True, slots=True)
class Inl:
    value: "Term"
    right_type: "Term"


@dataclass(frozen=True, slots=True)
class Inr:
    left_type: "Term"
    value: "Term"


@dataclass(frozen=True, slots=True)
class Case:
    scrutinee: "Term"
    left_branch: "Term"
    right_branch: "Term"
    result_type: "Term"


@dataclass(frozen=True, slots=True)
class EmptyType:
    pass


@dataclass(frozen=True, slots=True)
class EmptyElim:
    proof: "Term"
    result_type: "Term"


Term: TypeAlias = Union[
    Sort,
    Var,
    Const,
    Pi,
    Lam,
    App,
    Let,
    SumType,
    Inl,
    Inr,
    Case,
    EmptyType,
    EmptyElim,
]

PROP = Sort(0)
EMPTY = EmptyType()
