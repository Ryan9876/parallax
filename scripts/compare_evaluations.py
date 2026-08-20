from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare protected baseline/challenger promotion evidence.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("challenger", type=Path)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evaluation-evidence"))
    args = parser.parse_args()

    service = Path(__file__).resolve().parents[1] / "services" / "api"
    sys.path.insert(0, str(service))
    from parallax_api.evaluation.loader import load_evaluation_artifact
    from parallax_api.evaluation.promotion import compare_promotion_artifacts, write_promotion_decision

    try:
        baseline = load_evaluation_artifact(args.baseline)
        challenger = load_evaluation_artifact(args.challenger)
        decision = compare_promotion_artifacts(baseline, challenger)
        target = write_promotion_decision(decision, args.evidence_dir)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    state = "PASS" if decision.passed else "FAIL"
    reasons = ",".join(decision.reasons) if decision.reasons else "none"
    print(f"{state}: promotion aggregate_delta={decision.aggregate_delta:.4f} reasons={reasons} evidence={target}")
    return 0 if decision.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
