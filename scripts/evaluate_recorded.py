from __future__ import annotations

import argparse
from pathlib import Path
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate recorded Parallax candidate outputs.")
    parser.add_argument("suite", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--evidence-dir", type=Path, default=Path("evaluation-evidence"))
    args = parser.parse_args()

    service = Path(__file__).resolve().parents[1] / "services" / "api"
    sys.path.insert(0, str(service))
    from parallax_api.evaluation.loader import load_candidate, load_suite
    from parallax_api.evaluation.runner import evaluate_recorded_candidate, write_evaluation_artifact

    try:
        suite = load_suite(args.suite)
        candidate = load_candidate(args.candidate)
        artifact = evaluate_recorded_candidate(suite, candidate)
        target = write_evaluation_artifact(artifact, args.evidence_dir)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    state = "PASS" if artifact.protected_pass else "FAIL"
    print(f"{state}: {suite.suite_id}@{suite.suite_version} score={artifact.aggregate_score:.4f} evidence={target}")
    return 0 if artifact.protected_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
