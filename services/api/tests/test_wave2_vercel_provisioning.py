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


def test_plaintext_token_is_parsed_only_from_expected_vercel_token_shapes():
    assert provisioning._json_token('{"token":"vcp_example_project_token"}') == "vcp_example_project_token"
    assert provisioning._json_token('{"nested":{"value":"vca_example_access_token"}}') == "vca_example_access_token"

    with pytest.raises(provisioning.ProvisioningError, match="plaintext access token"):
        provisioning._json_token('{"token":"not-a-vercel-token"}')


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
