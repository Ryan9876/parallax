from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "https://parallax-api-tan.vercel.app"
PROOF_BRANCH = "control/w4-final-source-delivery-proof-7"
RUN_ID = "a92cb2f4-7816-4011-82a9-2cc111b737e9"
OPERATION_KEY = f"w4-final-prod-source-delivery-{RUN_ID}"


def _request_json(*, token: str, path: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: float = 600.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"diagnostic {method} {path} failed with HTTP {exc.code}: {raw[:1200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"diagnostic {method} {path} returned non-object response")
    return payload


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != PROOF_BRANCH:
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("diagnostic requires existing PARALLAX_ACCESS_TOKEN")

    before = _request_json(token=token, path=f"/v1/engineering-runs/{RUN_ID}")
    state = before.get("state")
    revision = before.get("revision")
    if not isinstance(revision, int):
        raise RuntimeError(f"diagnostic run revision is invalid: {before!r}")

    autonomy: dict[str, Any] | None = None
    if state == "IMPLEMENT":
        autonomy = _request_json(
            token=token,
            path=f"/v1/engineering-runs/{RUN_ID}/autonomous",
            method="POST",
            body={"operation_key": OPERATION_KEY, "expected_revision": revision},
            timeout=600.0,
        )
        print("AUTONOMY_RESPONSE=" + json.dumps(autonomy, sort_keys=True))

    after = _request_json(token=token, path=f"/v1/engineering-runs/{RUN_ID}")
    events = _request_json(token=token, path=f"/v1/engineering-runs/{RUN_ID}/events?after_sequence=0&limit=200")
    summary = {
        "run_id": RUN_ID,
        "before_state": state,
        "before_revision": revision,
        "after_state": after.get("state"),
        "after_revision": after.get("revision"),
        "last_failure_code": after.get("last_failure_code"),
        "stop_reason": autonomy.get("stop_reason") if isinstance(autonomy, dict) else None,
        "steps": autonomy.get("steps") if isinstance(autonomy, dict) else None,
        "attempts": [
            {"stage": item.get("stage"), "status": item.get("status"), "failure_code": item.get("failure_code")}
            for item in after.get("attempts", [])
            if isinstance(item, dict)
        ],
        "events": [
            {
                "sequence": item.get("sequence"),
                "event_type": item.get("event_type"),
                "stage": item.get("stage"),
                "outcome": item.get("outcome"),
                "failure_code": item.get("failure_code"),
                "metadata": item.get("metadata"),
            }
            for item in events.get("events", [])
            if isinstance(item, dict)
        ],
    }
    print("IMPLEMENT_DIAGNOSTIC=" + json.dumps(summary, sort_keys=True))

    if after.get("state") == "REVIEW":
        deliveries = [
            item
            for item in events.get("events", [])
            if isinstance(item, dict)
            and item.get("event_type") == "SOURCE_DELIVERY"
            and item.get("outcome") == "SUCCEEDED"
        ]
        if len(deliveries) != 1:
            raise RuntimeError(f"run reached REVIEW without exactly one successful SOURCE_DELIVERY: {deliveries!r}")
        print("W4 protected IMPLEMENT retry advanced through successful SOURCE_DELIVERY")
        return

    reason = autonomy.get("stop_reason") if isinstance(autonomy, dict) else "NO_AUTONOMY_RESPONSE"
    steps = autonomy.get("steps") if isinstance(autonomy, dict) else None
    raise RuntimeError(f"protected implementation retry did not reach REVIEW: state={after.get('state')!r} stop_reason={reason!r} steps={steps!r}")


if __name__ == "__main__":
    main()
