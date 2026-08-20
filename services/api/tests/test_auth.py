from __future__ import annotations

from fastapi.testclient import TestClient

from parallax_api.config import settings
from parallax_api.main import create_app


def test_operational_probes_are_public_but_application_routes_require_bearer():
    original = settings.access_token
    object.__setattr__(settings, "access_token", "a" * 32)
    try:
        client = TestClient(create_app(create_schema=True))
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200

        denied = client.get("/v1/conversations")
        assert denied.status_code == 401
        assert denied.json() == {"detail": "Authentication required"}

        invalid = client.get("/v1/conversations", headers={"Authorization": "Bearer wrong"})
        assert invalid.status_code == 401

        allowed = client.get(
            "/v1/conversations",
            headers={"Authorization": f"Bearer {'a' * 32}"},
        )
        assert allowed.status_code == 200
    finally:
        object.__setattr__(settings, "access_token", original)
