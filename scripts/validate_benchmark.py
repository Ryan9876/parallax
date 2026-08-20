from __future__ import annotations

from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_benchmark.py <suite.json>", file=sys.stderr)
        return 2
    service = Path(__file__).resolve().parents[1] / "services" / "api"
    sys.path.insert(0, str(service))
    from parallax_api.evaluation.loader import load_suite

    try:
        suite = load_suite(sys.argv[1])
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {suite.suite_id}@{suite.suite_version} purpose={suite.purpose} cases={len(suite.cases)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
