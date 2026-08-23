from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "provision_wave2_vercel.py"
SPEC = importlib.util.spec_from_file_location("provision_wave2_vercel", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
provisioning = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(provisioning)


def test_target_registry_is_exact_and_contains_only_credential_references():
    payload = json.loads(provisioning.target_registry_json())

    assert payload == [
        {
            "vercel_project_ref": "vercel:preview:parallax",
            "project_id": "prj_wLXC5JjjetJf0H97kncRlqczD3OC",
            "project_name": "parallax",
            "team_id": "team_JgE8AWWz36uzRbeR6V6EWg9k",
            "repository_ref": "github:Ryan9876/parallax",
            "github_repo_id": 1340272514,
            "production_branch": "main",
            "github_connector": "github/parallax-runtime",
            "vercel_token_env": "PARALLAX_VERCEL_TOKEN_PARALLAX",
        }
    ]
    assert "vcp_" not in provisioning.target_registry_json()
    assert "vca_" not in provisioning.target_registry_json()


def test_plaintext_token_parser_accepts_current_and_legacy_vercel_shapes():
    assert provisioning._json_token('{"bearerToken":"uRK_example_current_token"}') == "uRK_example_current_token"
    assert provisioning._json_token('{"token":"vcp_example_project_token"}') == "vcp_example_project_token"
    assert provisioning._json_token('{"nested":{"value":"vca_example_access_token"}}') == "vca_example_access_token"

    with pytest.raises(provisioning.ProvisioningError, match="plaintext access token"):
        provisioning._json_token('{"bearerToken":"bad token with spaces"}')


def test_environment_key_parser_never_requires_secret_values():
    keys = provisioning._env_keys(
        json.dumps(
            {
                "envs": [
                    {"key": "BLOB_READ_WRITE_TOKEN", "type": "sensitive"},
                    {"key": "PARALLAX_VERCEL_TOKEN_PARALLAX", "type": "sensitive"},
                    {"key": "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON", "type": "plain"},
                ]
            }
        )
    )

    assert keys == {
        "BLOB_READ_WRITE_TOKEN",
        "PARALLAX_VERCEL_TOKEN_PARALLAX",
        "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON",
    }


def test_canonical_project_link_is_seeded_without_user_identity_lookup(tmp_path):
    provisioning._ensure_link(tmp_path)
    assert json.loads((tmp_path / ".vercel" / "project.json").read_text()) == {
        "orgId": "team_JgE8AWWz36uzRbeR6V6EWg9k",
        "projectId": "prj_4lhve1AXZntfauaGHvkuaGWC6KJX",
    }


def test_canonical_project_link_rejects_wrong_existing_project(tmp_path):
    link_dir = tmp_path / ".vercel"
    link_dir.mkdir()
    (link_dir / "project.json").write_text('{"orgId":"wrong","projectId":"wrong"}')

    with pytest.raises(provisioning.ProvisioningError, match="does not match parallax-api"):
        provisioning._ensure_link(tmp_path)


def test_team_connector_inventory_is_used_before_project_attachment(monkeypatch, tmp_path):
    captured: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = '{"connectors":[{"uid":"github/parallax-runtime"}]}'
        stderr = ""

    def fake_run(args, **kwargs):
        captured.append(args)
        return Result()

    monkeypatch.setattr(provisioning, "_run", fake_run)
    assert provisioning._connector_present(tmp_path) is True
    assert captured == [["vercel", "connect", "list", "--all-projects", "--format=json"]]


def test_management_env_upsert_targets_preview_and_production_without_logging_value(monkeypatch):
    secret = "current_scoped_token_value"
    captured: dict[str, object] = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"created":{}}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.headers.get("Authorization")
        assert timeout == 20
        return Response()

    monkeypatch.setenv("VERCEL_TOKEN", "bootstrap-management-token")
    monkeypatch.setattr(provisioning, "urlopen", fake_urlopen)

    assert provisioning._set_env_via_api("PARALLAX_VERCEL_TOKEN_PARALLAX", secret, sensitive=True)
    assert captured["body"] == {
        "key": "PARALLAX_VERCEL_TOKEN_PARALLAX",
        "value": secret,
        "type": "sensitive",
        "target": ["preview", "production"],
        "comment": "Parallax Wave 2 bounded runtime prerequisite",
    }
    assert "upsert=true" in str(captured["url"])
    assert secret not in str(captured["url"])
    assert captured["authorization"] == "Bearer bootstrap-management-token"


def test_failed_cli_command_redacts_secret_from_exception(tmp_path):
    secret = "vcp_super_sensitive_test_value"

    with pytest.raises(provisioning.ProvisioningError) as failure:
        provisioning._run(
            [sys.executable, "-c", f"import sys; sys.stderr.write('{secret}'); raise SystemExit(1)"],
            cwd=tmp_path,
            secrets=(secret,),
        )

    assert secret not in str(failure.value)
    assert "<redacted>" in str(failure.value)
