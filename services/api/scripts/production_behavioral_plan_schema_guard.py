from __future__ import annotations

import os
from pathlib import Path
import sys

from sqlalchemy import inspect


_API_ROOT = Path(__file__).resolve().parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from parallax_api.db import make_engine


_TABLE = "behavioral_verification_plans"


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production behavioral-plan schema guard: SKIP "
            f"(VERCEL_ENV={environment}; production schema authority remains production-only)"
        )
        return

    engine = make_engine(environment="production")
    try:
        present = bool(inspect(engine).has_table(_TABLE))
    except Exception as exc:
        print(
            "Production behavioral-plan schema guard: FAIL "
            f"(stage=schema-observation; error={type(exc).__name__})",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    finally:
        engine.dispose()

    if not present:
        print(
            "Production behavioral-plan schema guard: BLOCK "
            "(behavioral_verification_plans is absent; P2-V0.23.47 routes cannot be promoted)",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("Production behavioral-plan schema guard: PASS (behavioral_verification_plans present)")


if __name__ == "__main__":
    main()
