from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def verify(path: Path) -> tuple[bool, str]:
    data = json.loads(path.read_text())
    head = "0" * 64
    for index, entry in enumerate(data.get("entries", [])):
        expected = hashlib.sha256(head.encode() + canonical(entry["event"])).hexdigest()
        if entry.get("previous") != head:
            return False, f"entry {index}: previous hash mismatch"
        if entry.get("digest") != expected:
            return False, f"entry {index}: digest mismatch"
        head = expected
    if data.get("head") != head:
        return False, "head mismatch"
    return True, head


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_audit.py <artifact.audit.json>", file=sys.stderr)
        return 2
    ok, detail = verify(Path(sys.argv[1]))
    print(json.dumps({"valid": ok, "detail": detail}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
