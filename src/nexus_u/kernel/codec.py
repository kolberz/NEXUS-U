from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .ast import App, Case, Const, EmptyElim, EmptyType, Inl, Inr, Lam, Let, Pi, Sort, SumType, Term, Var


def term_to_dict(term: Term) -> dict[str, Any]:
    if isinstance(term, Sort):
        return {"tag": "Sort", "level": term.level}
    if isinstance(term, Var):
        return {"tag": "Var", "index": term.index}
    if isinstance(term, Const):
        return {"tag": "Const", "name": term.name}
    if isinstance(term, Pi):
        return {"tag": "Pi", "domain": term_to_dict(term.domain), "codomain": term_to_dict(term.codomain)}
    if isinstance(term, Lam):
        return {"tag": "Lam", "domain": term_to_dict(term.domain), "body": term_to_dict(term.body)}
    if isinstance(term, App):
        return {"tag": "App", "function": term_to_dict(term.function), "argument": term_to_dict(term.argument)}
    if isinstance(term, Let):
        return {"tag": "Let", "annotation": term_to_dict(term.annotation), "value": term_to_dict(term.value), "body": term_to_dict(term.body)}
    if isinstance(term, SumType):
        return {"tag": "Sum", "left": term_to_dict(term.left), "right": term_to_dict(term.right)}
    if isinstance(term, Inl):
        return {"tag": "Inl", "value": term_to_dict(term.value), "right_type": term_to_dict(term.right_type)}
    if isinstance(term, Inr):
        return {"tag": "Inr", "left_type": term_to_dict(term.left_type), "value": term_to_dict(term.value)}
    if isinstance(term, Case):
        return {
            "tag": "Case",
            "scrutinee": term_to_dict(term.scrutinee),
            "left_branch": term_to_dict(term.left_branch),
            "right_branch": term_to_dict(term.right_branch),
            "result_type": term_to_dict(term.result_type),
        }
    if isinstance(term, EmptyType):
        return {"tag": "Empty"}
    if isinstance(term, EmptyElim):
        return {"tag": "EmptyElim", "proof": term_to_dict(term.proof), "result_type": term_to_dict(term.result_type)}
    raise TypeError(type(term).__name__)


def term_from_dict(data: dict[str, Any], *, depth: int = 0, max_depth: int = 10_000) -> Term:
    if depth > max_depth:
        raise ValueError("serialized term exceeds decoder depth limit")
    if not isinstance(data, dict) or "tag" not in data:
        raise ValueError("term must be an object with a tag")
    tag = data["tag"]
    recurse = lambda item: term_from_dict(item, depth=depth + 1, max_depth=max_depth)
    if tag == "Sort":
        return Sort(int(data["level"]))
    if tag == "Var":
        return Var(int(data["index"]))
    if tag == "Const":
        return Const(str(data["name"]))
    if tag == "Pi":
        return Pi(recurse(data["domain"]), recurse(data["codomain"]))
    if tag == "Lam":
        return Lam(recurse(data["domain"]), recurse(data["body"]))
    if tag == "App":
        return App(recurse(data["function"]), recurse(data["argument"]))
    if tag == "Let":
        return Let(recurse(data["annotation"]), recurse(data["value"]), recurse(data["body"]))
    if tag == "Sum":
        return SumType(recurse(data["left"]), recurse(data["right"]))
    if tag == "Inl":
        return Inl(recurse(data["value"]), recurse(data["right_type"]))
    if tag == "Inr":
        return Inr(recurse(data["left_type"]), recurse(data["value"]))
    if tag == "Case":
        return Case(recurse(data["scrutinee"]), recurse(data["left_branch"]), recurse(data["right_branch"]), recurse(data["result_type"]))
    if tag == "Empty":
        return EmptyType()
    if tag == "EmptyElim":
        return EmptyElim(recurse(data["proof"]), recurse(data["result_type"]))
    raise ValueError(f"unknown term tag: {tag}")


def write_json(data: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def read_json(path: str | Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value
