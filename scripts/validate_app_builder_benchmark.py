from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

SERVICE = Path(__file__).resolve().parents[1] / "services" / "api"
sys.path.insert(0, str(SERVICE))

from pydantic import ValidationError  # noqa: E402

from parallax_api.evaluation.app_builder import (  # noqa: E402
    evaluate_app_builder,
    load_app_builder_evidence,
    load_app_builder_suite,
    write_app_builder_report,
)
from parallax_api.evaluation.security import SecurityViolation  # noqa: E402


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Validate a Parallax app-builder benchmark and recorded evidence.")
    result.add_argument("--suite", type=Path, required=True)
    result.add_argument("--evidence", type=Path)
    result.add_argument("--report", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        suite = load_app_builder_suite(args.suite)
        if args.evidence is None:
            print(
                f"PASS: {suite.suite_id} {suite.suite_version} ({suite.purpose}) "
                f"covers {len(suite.cases)} cases"
            )
            return 0

        evidence = load_app_builder_evidence(args.evidence)
        report = evaluate_app_builder(suite, evidence)
        if args.report is not None:
            write_app_builder_report(report, args.report)

        status = "PASS" if report.protected_pass else "FAIL"
        print(
            f"{status}: {report.suite_id} {report.suite_version} ({report.suite_purpose}) "
            f"aggregate={report.aggregate_score:.4f} floor={report.minimum_aggregate_score:.4f} "
            f"report={report.report_id}"
        )
        for case in report.case_results:
            if not case.passed:
                print(f"FAIL: {case.case_id}: {','.join(case.failures)}")
        return 0 if report.protected_pass else 1
    except (OSError, json.JSONDecodeError, ValidationError, ValueError, SecurityViolation) as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
