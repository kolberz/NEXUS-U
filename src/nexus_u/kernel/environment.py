from __future__ import annotations

from dataclasses import dataclass, field

from .ast import Term


class EnvironmentError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Declaration:
    type: Term
    value: Term | None = None
    opaque: bool = False


@dataclass(slots=True)
class Environment:
    declarations: dict[str, Declaration] = field(default_factory=dict)
    axioms: set[str] = field(default_factory=set)

    def lookup(self, name: str) -> Declaration:
        try:
            return self.declarations[name]
        except KeyError as exc:
            raise EnvironmentError(f"unknown constant: {name}") from exc

    def add_definition(
        self,
        name: str,
        type_: Term,
        value: Term,
        *,
        opaque: bool = False,
    ) -> None:
        if name in self.declarations:
            raise EnvironmentError(f"constant already declared: {name}")
        self.declarations[name] = Declaration(type=type_, value=value, opaque=opaque)

    def add_axiom(self, name: str, type_: Term) -> None:
        if name in self.declarations:
            raise EnvironmentError(f"constant already declared: {name}")
        self.declarations[name] = Declaration(type=type_, value=None, opaque=True)
        self.axioms.add(name)
