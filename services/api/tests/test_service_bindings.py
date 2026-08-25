from __future__ import annotations

from dataclasses import fields

import pytest

from parallax_api.code.governed_skills import CapabilitySnapshot
from parallax_api.code.service_bindings import (
    AllowedAdapter,
    ProjectServiceBinding,
    ProjectServiceBindingRegistry,
    ServiceBindingAdmissionPolicy,
    ServiceBindingApproval,
    ServiceBindingError,
    ServiceBindingFailureCode,
    ServiceBindingResolution,
    ServiceBindingResolutionStatus,
    ServiceBindingResolver,
    ServiceRequirement,
    public_contract_field_names,
    record_service_binding_resolution,
)


PROJECT_ID = "11111111-1111-4111-8111-111111111111"
OTHER_PROJECT_ID = "22222222-2222-4222-8222-222222222222"
RUN_ID = "33333333-3333-4333-8333-333333333333"
POLICY_DIGEST = "a" * 64


def _binding(
    *,
    binding_id: str = "primary-db",
    project_id: str = PROJECT_ID,
    version: str = "1.0.0",
    service_id: str = "database",
    interface_version: str = "database.v1",
    adapter_id: str = "postgres-adapter",
    adapter_version: str = "1.0.0",
    supported_features: tuple[str, ...] = ("migrations", "transactions"),
    secret_slot_ids: tuple[str, ...] = ("database-url",),
    priority: int = 50,
) -> ProjectServiceBinding:
    return ProjectServiceBinding(
        project_id=project_id,
        binding_id=binding_id,
        version=version,
        service_id=service_id,
        interface_version=interface_version,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        supported_features=supported_features,
        secret_slot_ids=secret_slot_ids,
        priority=priority,
    )


def _policy(
    *bindings: ProjectServiceBinding,
    project_id: str = PROJECT_ID,
    declarable_services: tuple[str, ...] = ("database", "object-store"),
    declarable_adapters: tuple[AllowedAdapter, ...] = (
        AllowedAdapter("postgres-adapter", "1.0.0"),
        AllowedAdapter("object-store-adapter", "1.0.0"),
    ),
    declarable_secret_slots: tuple[str, ...] = ("database-url", "object-store-key"),
) -> ServiceBindingAdmissionPolicy:
    if not bindings:
        bindings = (_binding(project_id=project_id),)
    approvals = tuple(
        ServiceBindingApproval(
            project_id=project_id,
            binding_id=binding.binding_id,
            version=binding.version,
            content_digest=binding.digest,
        )
        for binding in bindings
    )
    return ServiceBindingAdmissionPolicy(
        project_id=project_id,
        approvals=approvals,
        declarable_services=declarable_services,
        declarable_adapters=declarable_adapters,
        declarable_secret_slots=declarable_secret_slots,
    )


def _registry(*bindings: ProjectServiceBinding) -> ProjectServiceBindingRegistry:
    if not bindings:
        bindings = (_binding(),)
    registry = ProjectServiceBindingRegistry(_policy(*bindings))
    for binding in bindings:
        registry.admit(binding)
    return registry


def test_requirement_and_binding_digests_are_order_independent_and_project_bound():
    req_a = ServiceRequirement("database", "database.v1", ("transactions", "migrations"))
    req_b = ServiceRequirement("database", "database.v1", ("migrations", "transactions"))
    assert req_a.required_features == ("migrations", "transactions")
    assert req_a.digest == req_b.digest

    binding_a = _binding(
        supported_features=("transactions", "migrations"),
        secret_slot_ids=("database-url",),
    )
    binding_b = _binding(
        supported_features=("migrations", "transactions"),
        secret_slot_ids=("database-url",),
    )
    assert binding_a.digest == binding_b.digest
    assert _binding(project_id=OTHER_PROJECT_ID).digest != binding_a.digest


def test_exact_project_scoped_admission_is_idempotent():
    binding = _binding()
    registry = ProjectServiceBindingRegistry(_policy(binding))

    first = registry.admit(binding)
    second = registry.admit(binding)

    assert first is second
    assert first.content_digest == binding.digest
    assert registry.project_id == PROJECT_ID
    assert first.safe_metadata()["grants_authority"] is False
    assert first.safe_metadata()["contains_secret_values"] is False
    assert first.safe_metadata()["contains_secret_handles"] is False


def test_cross_project_admission_fails_before_registry_mutation():
    binding = _binding(project_id=OTHER_PROJECT_ID)
    registry = ProjectServiceBindingRegistry(_policy(_binding()))

    with pytest.raises(ServiceBindingError) as exc:
        registry.admit(binding)

    assert exc.value.code is ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH
    assert registry.registered() == ()


def test_same_version_changed_digest_is_conflict_before_approval_check():
    approved = _binding(priority=50)
    changed = _binding(priority=51)
    registry = ProjectServiceBindingRegistry(_policy(approved))
    registry.admit(approved)

    with pytest.raises(ServiceBindingError) as exc:
        registry.admit(changed)

    assert exc.value.code is ServiceBindingFailureCode.BINDING_VERSION_CONFLICT
    assert registry.registered()[0].content_digest == approved.digest


def test_unapproved_digest_fails_closed():
    approved = _binding(priority=50)
    unapproved = _binding(binding_id="secondary-db", priority=60)
    registry = ProjectServiceBindingRegistry(_policy(approved))

    with pytest.raises(ServiceBindingError) as exc:
        registry.admit(unapproved)

    assert exc.value.code is ServiceBindingFailureCode.BINDING_NOT_APPROVED


@pytest.mark.parametrize(
    ("policy_kwargs", "expected"),
    [
        ({"declarable_services": ("object-store",)}, ServiceBindingFailureCode.SERVICE_NOT_DECLARABLE),
        (
            {"declarable_adapters": (AllowedAdapter("object-store-adapter", "1.0.0"),)},
            ServiceBindingFailureCode.ADAPTER_NOT_DECLARABLE,
        ),
        ({"declarable_secret_slots": ("object-store-key",)}, ServiceBindingFailureCode.SECRET_SLOT_NOT_DECLARABLE),
    ],
)
def test_server_owned_declaration_policy_rejects_unregistered_authority(policy_kwargs, expected):
    binding = _binding()
    registry = ProjectServiceBindingRegistry(_policy(binding, **policy_kwargs))

    with pytest.raises(ServiceBindingError) as exc:
        registry.admit(binding)

    assert exc.value.code is expected
    assert registry.registered() == ()


def test_registry_order_and_resolution_are_deterministic_across_process_recreation():
    lower = _binding(binding_id="lower-db", priority=20)
    higher = _binding(binding_id="higher-db", version="2.0.0", priority=80)
    policy = _policy(lower, higher)

    first = ProjectServiceBindingRegistry(policy)
    first.admit(lower)
    first.admit(higher)
    second = ProjectServiceBindingRegistry(policy)
    second.admit(higher)
    second.admit(lower)

    assert [item.key for item in first.registered()] == [item.key for item in second.registered()]

    requirement = ServiceRequirement("database", "database.v1", ("transactions",))
    result_a = ServiceBindingResolver(first).resolve(project_id=PROJECT_ID, requirement=requirement)
    result_b = ServiceBindingResolver(second).resolve(project_id=PROJECT_ID, requirement=requirement)

    assert result_a == result_b
    assert result_a.status is ServiceBindingResolutionStatus.SELECTED
    assert result_a.binding_id == "higher-db"
    assert result_a.grants_authority is False if hasattr(result_a, "grants_authority") else True
    assert result_a.as_dict()["grants_authority"] is False


def test_missing_incompatible_and_ambiguous_bindings_require_human_action():
    primary = _binding(binding_id="primary-db", priority=50)
    tied = _binding(binding_id="tied-db", version="2.0.0", priority=50)
    registry = _registry(primary, tied)
    resolver = ServiceBindingResolver(registry)

    missing = resolver.resolve(
        project_id=PROJECT_ID,
        requirement=ServiceRequirement("object-store", "object-store.v1"),
    )
    assert missing.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED
    assert missing.reason is ServiceBindingFailureCode.NO_BINDING_AVAILABLE

    incompatible_interface = resolver.resolve(
        project_id=PROJECT_ID,
        requirement=ServiceRequirement("database", "database.v2"),
    )
    assert incompatible_interface.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED
    assert incompatible_interface.reason is ServiceBindingFailureCode.INCOMPATIBLE_BINDING

    incompatible_feature = resolver.resolve(
        project_id=PROJECT_ID,
        requirement=ServiceRequirement("database", "database.v1", ("replication",)),
    )
    assert incompatible_feature.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED
    assert incompatible_feature.reason is ServiceBindingFailureCode.INCOMPATIBLE_BINDING

    ambiguous = resolver.resolve(
        project_id=PROJECT_ID,
        requirement=ServiceRequirement("database", "database.v1", ("transactions",)),
    )
    assert ambiguous.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED
    assert ambiguous.reason is ServiceBindingFailureCode.AMBIGUOUS_BINDING_SELECTION
    assert ambiguous.binding_id is None
    assert ambiguous.as_dict()["grants_authority"] is False


def test_resolution_rejects_cross_project_identity():
    resolver = ServiceBindingResolver(_registry(_binding()))

    with pytest.raises(ServiceBindingError) as exc:
        resolver.resolve(
            project_id=OTHER_PROJECT_ID,
            requirement=ServiceRequirement("database", "database.v1"),
        )

    assert exc.value.code is ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH


def test_resolution_record_is_replay_stable_and_contains_only_bounded_metadata():
    binding = _binding(priority=80)
    policy = _policy(binding)
    registry = ProjectServiceBindingRegistry(policy)
    registered = registry.admit(binding)
    requirement = ServiceRequirement("database", "database.v1", ("transactions",))
    resolution = ServiceBindingResolver(registry).resolve(project_id=PROJECT_ID, requirement=requirement)

    first = record_service_binding_resolution(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        requirement=requirement,
        policy=policy,
        resolution=resolution,
        registered_binding=registered,
    )
    second = record_service_binding_resolution(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        requirement=requirement,
        policy=policy,
        resolution=resolution,
        registered_binding=registered,
    )

    assert first == second
    assert first.resolution_id.startswith("bindingres:")
    payload = first.as_dict()
    assert payload["contains_raw_application_payload"] is False
    assert payload["contains_secret_values"] is False
    assert payload["contains_secret_handles"] is False
    assert payload["contains_provider_payload"] is False
    assert payload["grants_authority"] is False
    assert "postgres://" not in repr(payload)


def test_human_required_resolution_record_is_replayable_without_binding_or_secret_material():
    binding = _binding()
    policy = _policy(binding)
    requirement = ServiceRequirement("object-store", "object-store.v1")
    resolution = ServiceBindingResolver(_registry(binding)).resolve(
        project_id=PROJECT_ID,
        requirement=requirement,
    )

    record = record_service_binding_resolution(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        requirement=requirement,
        policy=policy,
        resolution=resolution,
    )

    assert record.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED
    assert record.binding_id is None
    assert record.secret_slot_ids == ()
    assert record.as_dict()["contains_secret_handles"] is False


def test_tampered_selected_resolution_cannot_be_recorded_as_evidence():
    binding = _binding()
    policy = _policy(binding)
    registry = ProjectServiceBindingRegistry(policy)
    registered = registry.admit(binding)
    requirement = ServiceRequirement("database", "database.v1")
    selected = ServiceBindingResolver(registry).resolve(project_id=PROJECT_ID, requirement=requirement)
    tampered = ServiceBindingResolution(
        status=selected.status,
        reason=None,
        binding_id=selected.binding_id,
        binding_version=selected.binding_version,
        binding_digest=selected.binding_digest,
        adapter_id="object-store-adapter",
        adapter_version=selected.adapter_version,
        supported_features=selected.supported_features,
        secret_slot_ids=selected.secret_slot_ids,
    )

    with pytest.raises(ServiceBindingError) as exc:
        record_service_binding_resolution(
            project_id=PROJECT_ID,
            run_id=RUN_ID,
            requirement=requirement,
            policy=policy,
            resolution=tampered,
            registered_binding=registered,
        )

    assert exc.value.code is ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH


def test_public_contracts_structurally_exclude_generic_provider_and_secret_value_surfaces():
    names = set(public_contract_field_names())
    forbidden = {
        "url",
        "host",
        "http_method",
        "http_body",
        "headers",
        "environment",
        "environment_variables",
        "secret_value",
        "secret_handle",
        "credential",
        "token",
        "connection_string",
        "command",
        "source_path",
        "deployment_target",
        "provider_payload",
    }
    assert names.isdisjoint(forbidden)
    assert "secret_slot_ids" in names

    binding_fields = {item.name for item in fields(ProjectServiceBinding)}
    assert binding_fields.isdisjoint(forbidden)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ServiceRequirement("https://evil.example", "database.v1"),
        lambda: ProjectServiceBinding(
            project_id=PROJECT_ID,
            binding_id="bad-provider",
            version="1.0.0",
            service_id="database",
            interface_version="database.v1",
            adapter_id="https://evil.example",
            adapter_version="1.0.0",
        ),
        lambda: ProjectServiceBinding(
            project_id=PROJECT_ID,
            binding_id="bad-slot",
            version="1.0.0",
            service_id="database",
            interface_version="database.v1",
            adapter_id="postgres-adapter",
            adapter_version="1.0.0",
            secret_slot_ids=("DATABASE_URL=postgres://secret",),
        ),
    ],
)
def test_malicious_provider_url_and_secret_value_attempts_fail_contract_validation(factory):
    with pytest.raises(ServiceBindingError) as exc:
        factory()
    assert exc.value.code is ServiceBindingFailureCode.INVALID_BINDING_CONTRACT


def test_s1_s2_evidence_cannot_expand_service_binding_authority_or_capabilities():
    binding = _binding()
    registry = _registry(binding)
    capability_snapshot = CapabilitySnapshot(("preview.deploy",), POLICY_DIGEST)
    before = capability_snapshot.safe_metadata()

    selected = ServiceBindingResolver(registry).resolve(
        project_id=PROJECT_ID,
        requirement=ServiceRequirement("database", "database.v1"),
    )

    assert selected.status is ServiceBindingResolutionStatus.SELECTED
    assert capability_snapshot.safe_metadata() == before
    assert capability_snapshot.capability_ids == ("preview.deploy",)
    assert selected.as_dict()["grants_authority"] is False
    assert "capability_ids" not in selected.as_dict()

    # The S3 registry has no repository profile, skill contract, procedure text,
    # capability snapshot, provider payload, or model-output admission method.
    registry_api = {name for name in dir(registry) if not name.startswith("_")}
    assert registry_api == {"admit", "policy", "project_id", "registered"}
