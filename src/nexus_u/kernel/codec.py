from __future__ import annotations

import hashlib
import json
from typing import Any

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


class DecodeError(ValueError):
    pass


def encode_term(term: Term) -> dict[str, Any]:
    match term:
        case Sort(level=level):
            return {"tag": "Sort", "level": level}
        case Var(index=index):
            return {"tag": "Var", "index": index}
        case Const(name=name):
            return {"tag": "Const", "name": name}
        case Pi(domain=domain, codomain=codomain):
            return {"tag": "Pi", "domain": encode_term(domain), "codomain": encode_term(codomain)}
        case Lam(domain=domain, body=body):
            return {"tag": "Lam", "domain": encode_term(domain), "body": encode_term(body)}
        case App(function=function, argument=argument):
            return {"tag": "App", "function": encode_term(function), "argument": encode_term(argument)}
        case Let(value_type=value_type, value=value, body=body):
            return {
                "tag": "Let",
                "value_type": encode_term(value_type),
                "value": encode_term(value),
                "body": encode_term(body),
            }
        case Empty():
            return {"tag": "Empty"}
        case EmptyElim(result_type=result_type, proof=proof):
            return {"tag": "EmptyElim", "result_type": encode_term(result_type), "proof": encode_term(proof)}
        case Sum(left=left, right=right):
            return {"tag": "Sum", "left": encode_term(left), "right": encode_term(right)}
        case Inl(value=value, right_type=right_type):
            return {"tag": "Inl", "value": encode_term(value), "right_type": encode_term(right_type)}
        case Inr(value=value, left_type=left_type):
            return {"tag": "Inr", "value": encode_term(value), "left_type": encode_term(left_type)}
        case Case(scrutinee=scrutinee, left_branch=left_branch, right_branch=right_branch, result_type=result_type):
            return {
                "tag": "Case",
                "scrutinee": encode_term(scrutinee),
                "left_branch": encode_term(left_branch),
                "right_branch": encode_term(right_branch),
                "result_type": encode_term(result_type),
            }
        case _:
            raise TypeError(f"unsupported term: {type(term).__name__}")


def decode_term(payload: Any, *, max_depth: int = 512, _depth: int = 0) -> Term:
    if _depth > max_depth:
        raise DecodeError("decoder depth limit exceeded")
    if not isinstance(payload, dict):
        raise DecodeError("term payload must be an object")
    tag = payload.get("tag")
    child = lambda value: decode_term(value, max_depth=max_depth, _depth=_depth + 1)
    try:
        match tag:
            case "Sort":
                return Sort(int(payload["level"]))
            case "Var":
                return Var(int(payload["index"]))
            case "Const":
                return Const(str(payload["name"]))
            case "Pi":
                return Pi(child(payload["domain"]), child(payload["codomain"]))
            case "Lam":
                return Lam(child(payload["domain"]), child(payload["body"]))
            case "App":
                return App(child(payload["function"]), child(payload["argument"]))
            case "Let":
                return Let(child(payload["value_type"]), child(payload["value"]), child(payload["body"]))
            case "Empty":
                return Empty()
            case "EmptyElim":
                return EmptyElim(child(payload["result_type"]), child(payload["proof"]))
            case "Sum":
                return Sum(child(payload["left"]), child(payload["right"]))
            case "Inl":
                return Inl(child(payload["value"]), child(payload["right_type"]))
            case "Inr":
                return Inr(child(payload["value"]), child(payload["left_type"]))
            case "Case":
                return Case(
                    child(payload["scrutinee"]),
                    child(payload["left_branch"]),
                    child(payload["right_branch"]),
                    child(payload["result_type"]),
                )
            case _:
                raise DecodeError(f"unknown serialized term tag: {tag!r}")
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, DecodeError):
            raise
        raise DecodeError(f"invalid {tag!r} payload") from exc


def canonical_json(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()
