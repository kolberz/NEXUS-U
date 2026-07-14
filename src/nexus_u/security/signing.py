from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def hmac_sign(value: Any, secret: str | bytes) -> str:
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    return hmac.new(key, canonical_json(value), hashlib.sha256).hexdigest()


def hmac_verify(value: Any, signature: str, secret: str | bytes) -> bool:
    return hmac.compare_digest(hmac_sign(value, secret), signature)


def write_signed_envelope(payload: Any, path: Path | str, *, key_id: str, secret: str | bytes) -> Path:
    envelope = {
        "algorithm": "HMAC-SHA256",
        "key_id": key_id,
        "payload": payload,
        "signature": hmac_sign(payload, secret),
    }
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(envelope, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return output


def verify_signed_envelope(envelope: dict[str, Any], secret: str | bytes) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if envelope.get("algorithm") != "HMAC-SHA256":
        errors.append("Unsupported signature algorithm")
    if not envelope.get("key_id"):
        errors.append("Missing key identifier")
    if "payload" not in envelope or not envelope.get("signature"):
        errors.append("Incomplete signed envelope")
    elif not hmac_verify(envelope["payload"], str(envelope["signature"]), secret):
        errors.append("Signature mismatch")
    return not errors, errors
