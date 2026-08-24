from __future__ import annotations

import logging

from parallax_api.code.bootstrap_observability import (
    classify_bootstrap_failure,
    record_bootstrap_failure,
)
from parallax_api.code.lineage_persistence import MetadataStoreError, ObjectStoreError
from parallax_api.code.workspace_lineage import SourcePolicyError, SourceProviderError
from parallax_api.tools.providers import ProviderClientError


def _caused_by(outer: BaseException, cause: BaseException) -> BaseException:
    outer.__cause__ = cause
    return outer


def test_provider_failure_keeps_only_bounded_result_code() -> None:
    failure = _caused_by(
        SourceProviderError("source path /private/secret-token-value failed"),
        ProviderClientError("SOURCE_NOT_FOUND"),
    )

    evidence = classify_bootstrap_failure(failure, default_stage="lineage-initialize")

    assert evidence.stage == "provider-client"
    assert evidence.error_class == "ProviderClientError"
    assert evidence.result_code == "SOURCE_NOT_FOUND"


def test_durable_failure_classification_distinguishes_object_and_metadata_boundaries() -> None:
    object_evidence = classify_bootstrap_failure(
        ObjectStoreError("provider token should never be logged"),
        default_stage="lineage-initialize",
    )
    metadata_evidence = classify_bootstrap_failure(
        MetadataStoreError("database details should never be logged"),
        default_stage="lineage-initialize",
    )

    assert object_evidence.stage == "object-store"
    assert metadata_evidence.stage == "metadata-store"


def test_source_policy_failure_is_distinct_from_durable_failures() -> None:
    evidence = classify_bootstrap_failure(
        SourcePolicyError("secret-sensitive source path"),
        default_stage="lineage-initialize",
    )
    assert evidence.stage == "source-policy"
    assert evidence.error_class == "SourcePolicyError"
    assert evidence.result_code is None


def test_delivery_composition_stage_is_registered_and_does_not_emit_message_text(caplog) -> None:
    secret_marker = "never-log-delivery-config-secret"
    failure = RuntimeError(secret_marker)

    with caplog.at_level(logging.ERROR, logger="parallax.bootstrap"):
        evidence = record_bootstrap_failure(failure, default_stage="delivery-composition")

    assert evidence.stage == "delivery-composition"
    assert evidence.error_class == "RuntimeError"
    assert evidence.result_code is None
    assert "stage=delivery-composition" in caplog.text
    assert secret_marker not in caplog.text


def test_runtime_log_contains_only_stage_class_and_safe_code(caplog) -> None:
    secret_marker = "do-not-log-this-provider-secret"
    failure = _caused_by(
        SourceProviderError(f"raw provider failure {secret_marker}"),
        ProviderClientError("CREDENTIAL_UNAVAILABLE"),
    )

    with caplog.at_level(logging.ERROR, logger="parallax.bootstrap"):
        evidence = record_bootstrap_failure(failure, default_stage="lineage-initialize")

    assert evidence.stage == "provider-client"
    assert "stage=provider-client" in caplog.text
    assert "error_class=ProviderClientError" in caplog.text
    assert "result_code=CREDENTIAL_UNAVAILABLE" in caplog.text
    assert secret_marker not in caplog.text
