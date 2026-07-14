from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .benchmark import run_benchmark, verify_bundle, write_benchmark


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="nexus-u")
    root.add_argument("--version", action="version", version=__version__)
    sub = root.add_subparsers(dest="command")

    bench = sub.add_parser("nexus-kernel-benchmark", help="run the recovered native-kernel benchmark")
    bench.add_argument("--output", type=Path, default=Path("benchmark-results"))

    check = sub.add_parser("kernel-check", help="verify a serialized proof bundle")
    check.add_argument("bundle", type=Path)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "nexus-kernel-benchmark":
        result = write_benchmark(args.output)
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        return 0 if result["summary"]["all_checks_passed"] else 1
    if args.command == "kernel-check":
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        verify_bundle(bundle)
        print("NEXUS_KERNEL_VERIFIED_RECOVERED")
        return 0
    parser().print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
