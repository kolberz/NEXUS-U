from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .ast import Term


@dataclass(frozen=True, slots=True)
class Declaration:
    name: str
    type: Term
    value: Term | None = None
    opaque: bool = False

    @property
    def is_axiom(self) -> bool:
        return self.value is None


class Environment:
    def __init__(self, declarations: Iterable[Declaration] = ()) -> None:
        self._decls: dict[str, Declaration] = {}
        for declaration in declarations:
            self.add_unchecked(declaration)

    def add_unchecked(self, declaration: Declaration) -> None:
        if not declaration.name:
            raise ValueError("declaration names must be non-empty")
        if declaration.name in self._decls:
            raise ValueError(f"duplicate declaration: {declaration.name}")
        self._decls[declaration.name] = declaration

    def get(self, name: str) -> Declaration:
        try:
            return self._decls[name]
        except KeyError as exc:
            raise KeyError(f"unknown constant: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(self._decls)

    def declarations(self) -> tuple[Declaration, ...]:
        return tuple(self._decls.values())

    def axioms(self) -> tuple[str, ...]:
        return tuple(name for name, decl in self._decls.items() if decl.is_axiom)
