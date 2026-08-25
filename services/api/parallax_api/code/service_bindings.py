from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable
from uuid import UUID


SERVICE_BINDING_CONTRACT_VERSION = 1
_MAX_FEATURES = 32
_MAX_SECRET_SLOTS = 32
_MAX_APPROVALS = 128
_MAX_DECLARATIONS = 64
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ServiceBindingFailureCode(StrEnum):
    INVALID_BINDING_CONTRACT = "INVALID_BINDING_CONTRACT"
    PROJECT_IDENTITY_MISMATCH = "PROJECT_IDENTITY_MISMATCH"
    BINDING_NOT_APPROVED = "BINDING_NOT_APPROVED"
    BINDING_VERSION_CONFLICT = "BINDING_VERSION_CONFLICT"
    SERVICE_NOT_DECLARABLE = "SERVICE_NOT_DECLARABLE"
    ADAPTER_NOT_DECLARABLE = "ADAPTER_NOT_DECLARABLE"
    SECRET_SLOT_NOT_DECLARABLE = "SECRET_SLOT_NOT_DECLARABLE"
    NO_BINDING_AVAILABLE = "NO_BINDING_AVAILABLE"
    INCOMPATIBLE_BINDING = "INCOMPATIBLE_BINDING"
    AMBIGUOUS_BINDING_SELECTION = "AMBIGUOUS_BINDING_SELECTION"
    RESOLUTION_IDENTITY_MISMATCH = "RESOLUTION_IDENTITY_MISMATCH"


class ServiceBindingResolutionStatus(StrEnum):
    SELECTED = "SELECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class ServiceBindingError(ValueError):
    def __init__(self, code: ServiceBindingFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class ServiceRequirement:
    service_id: str
    interface_version: str
    required_features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_id", _safe_token(self.service_id))
        object.__setattr__(self, "interface_version", _safe_token(self.interface_version))
        object.__setattr__(
            self,
            "required_features",
            _bounded_tokens(self.required_features, limit=_MAX_FEATURES),
        )

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": SERVICE_BINDING_CONTRACT_VERSION,
            "service_id": self.service_id,
            "interface_version": self.interface_version,
            "required_features": list(self.required_features),
        }


@dataclass(frozen=True, slots=True)
class AllowedAdapter:
    adapter_id: str
    adapter_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _safe_token(self.adapter_id))
        object.__setattr__(self, "adapter_version", _semver(self.adapter_version))

    @property
    def key(self) -> tuple[str, str]:
        return self.adapter_id, self.adapter_version

    def as_dict(self) -> dict[str, str]:
        return {"adapter_id": self.adapter_id, "adapter_version": self.adapter_version}


@dataclass(frozen=True, slots=True)
class ProjectServiceBinding:
    project_id: str
    binding_id: str
    version: str
    service_id: str
    interface_version: str
    adapter_id: str
    adapter_version: str
    supported_features: tuple[str, ...] = ()
    secret_slot_ids: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id))
        object.__setattr__(self, "binding_id", _safe_token(self.binding_id))
        object.__setattr__(self, "version", _semver(self.version))
        object.__setattr__(self, "service_id", _safe_token(self.service_id))
        object.__setattr__(self, "interface_version", _safe_token(self.interface_version))
        object.__setattr__(self, "adapter_id", _safe_token(self.adapter_id))
        object.__setattr__(self, "adapter_version", _semver(self.adapter_version))
        object.__setattr__(
            self,
            "supported_features",
            _bounded_tokens(self.supported_features, limit=_MAX_FEATURES),
        )
        object.__setattr__(
            self,
            "secret_slot_ids",
            _bounded_tokens(self.secret_slot_ids, limit=_MAX_SECRET_SLOTS),
        )
        if not isinstance(self.priority, int) or isinstance(self.priority, bool) or not 0 <= self.priority <= 100:
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self._canonical_payload())).hexdigest()

    def _canonical_payload(self) -> dict[str, object]:
        return {
            "contract_version": SERVICE_BINDING_CONTRACT_VERSION,
            "project_id": self.project_id,
            "binding_id": self.binding_id,
            "version": self.version,
            "service_id": self.service_id,
            "interface_version": self.interface_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "supported_features": list(self.supported_features),
            "secret_slot_ids": list(self.secret_slot_ids),
            "priority": self.priority,
        }

    def safe_metadata(self) -> dict[str, object]:
        return {
            **self._canonical_payload(),
            "content_digest": self.digest,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class ServiceBindingApproval:
    project_id: str
    binding_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id))
        object.__setattr__(self, "binding_id", _safe_token(self.binding_id))
        object.__setattr__(self, "version", _semver(self.version))
        object.__setattr__(self, "content_digest", _sha256_digest(self.content_digest))

    @property
    def key(self) -> tuple[str, str]:
        return self.binding_id, self.version

    def as_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "binding_id": self.binding_id,
            "version": self.version,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class ServiceBindingAdmissionPolicy:
    project_id: str
    approvals: tuple[ServiceBindingApproval, ...]
    declarable_services: tuple[str, ...]
    declarable_adapters: tuple[AllowedAdapter, ...]
    declarable_secret_slots: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        project_id = _canonical_uuid(self.project_id)
        object.__setattr__(self, "project_id", project_id)

        approvals = tuple(self.approvals)
        if not approvals or len(approvals) > _MAX_APPROVALS:
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        if any(not isinstance(item, ServiceBindingApproval) for item in approvals):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        if any(item.project_id != project_id for item in approvals):
            raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH)
        approvals = tuple(sorted(approvals, key=lambda item: item.key))
        if len({item.key for item in approvals}) != len(approvals):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        object.__setattr__(self, "approvals", approvals)

        services = _bounded_tokens(self.declarable_services, limit=_MAX_DECLARATIONS, require_nonempty=True)
        object.__setattr__(self, "declarable_services", services)

        adapters = tuple(self.declarable_adapters)
        if not adapters or len(adapters) > _MAX_DECLARATIONS or any(
            not isinstance(item, AllowedAdapter) for item in adapters
        ):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        adapters = tuple(sorted(adapters, key=lambda item: item.key))
        if len({item.key for item in adapters}) != len(adapters):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        object.__setattr__(self, "declarable_adapters", adapters)

        slots = _bounded_tokens(self.declarable_secret_slots, limit=_MAX_SECRET_SLOTS)
        object.__setattr__(self, "declarable_secret_slots", slots)

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "project_id": self.project_id,
                    "approvals": [item.as_dict() for item in self.approvals],
                    "declarable_services": list(self.declarable_services),
                    "declarable_adapters": [item.as_dict() for item in self.declarable_adapters],
                    "declarable_secret_slots": list(self.declarable_secret_slots),
                }
            )
        ).hexdigest()

    def approved_digest(self, binding_id: str, version: str) -> str | None:
        for approval in self.approvals:
            if approval.binding_id == binding_id and approval.version == version:
                return approval.content_digest
        return None

    def adapter_allowed(self, adapter_id: str, adapter_version: str) -> bool:
        return (adapter_id, adapter_version) in {item.key for item in self.declarable_adapters}


@dataclass(frozen=True, slots=True)
class RegisteredServiceBinding:
    contract: ProjectServiceBinding
    content_digest: str
    admission_policy_digest: str

    def __post_init__(self) -> None:
        content_digest = _sha256_digest(self.content_digest)
        policy_digest = _sha256_digest(self.admission_policy_digest)
        if content_digest != self.contract.digest:
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        object.__setattr__(self, "content_digest", content_digest)
        object.__setattr__(self, "admission_policy_digest", policy_digest)

    @property
    def key(self) -> tuple[str, str]:
        return self.contract.binding_id, self.contract.version

    def safe_metadata(self) -> dict[str, object]:
        return {
            **self.contract.safe_metadata(),
            "admission_policy_digest": self.admission_policy_digest,
        }


class ProjectServiceBindingRegistry:
    def __init__(self, policy: ServiceBindingAdmissionPolicy) -> None:
        if not isinstance(policy, ServiceBindingAdmissionPolicy):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        self.policy = policy
        self._bindings: dict[tuple[str, str], RegisteredServiceBinding] = {}

    @property
    def project_id(self) -> str:
        return self.policy.project_id

    def admit(self, contract: ProjectServiceBinding) -> RegisteredServiceBinding:
        if not isinstance(contract, ProjectServiceBinding):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        if contract.project_id != self.policy.project_id:
            raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH)

        key = contract.binding_id, contract.version
        digest = contract.digest
        existing = self._bindings.get(key)
        if existing is not None:
            if existing.content_digest == digest:
                return existing
            raise ServiceBindingError(ServiceBindingFailureCode.BINDING_VERSION_CONFLICT)

        approved = self.policy.approved_digest(contract.binding_id, contract.version)
        if approved is None or approved != digest:
            raise ServiceBindingError(ServiceBindingFailureCode.BINDING_NOT_APPROVED)
        if contract.service_id not in self.policy.declarable_services:
            raise ServiceBindingError(ServiceBindingFailureCode.SERVICE_NOT_DECLARABLE)
        if not self.policy.adapter_allowed(contract.adapter_id, contract.adapter_version):
            raise ServiceBindingError(ServiceBindingFailureCode.ADAPTER_NOT_DECLARABLE)
        if not set(contract.secret_slot_ids).issubset(self.policy.declarable_secret_slots):
            raise ServiceBindingError(ServiceBindingFailureCode.SECRET_SLOT_NOT_DECLARABLE)

        registered = RegisteredServiceBinding(
            contract=contract,
            content_digest=digest,
            admission_policy_digest=self.policy.digest,
        )
        self._bindings[key] = registered
        return registered

    def registered(self) -> tuple[RegisteredServiceBinding, ...]:
        return tuple(self._bindings[key] for key in sorted(self._bindings))


@dataclass(frozen=True, slots=True)
class ServiceBindingResolution:
    status: ServiceBindingResolutionStatus
    reason: ServiceBindingFailureCode | None
    binding_id: str | None
    binding_version: str | None
    binding_digest: str | None
    adapter_id: str | None
    adapter_version: str | None
    supported_features: tuple[str, ...]
    secret_slot_ids: tuple[str, ...]

    @property
    def selected(self) -> bool:
        return self.status is ServiceBindingResolutionStatus.SELECTED

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason": self.reason.value if self.reason is not None else None,
            "binding_id": self.binding_id,
            "binding_version": self.binding_version,
            "binding_digest": self.binding_digest,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "supported_features": list(self.supported_features),
            "secret_slot_ids": list(self.secret_slot_ids),
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_authority": False,
        }


class ServiceBindingResolver:
    def __init__(self, registry: ProjectServiceBindingRegistry) -> None:
        if not isinstance(registry, ProjectServiceBindingRegistry):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
        self.registry = registry

    def resolve(self, *, project_id: str, requirement: ServiceRequirement) -> ServiceBindingResolution:
        project = _canonical_uuid(project_id)
        if project != self.registry.project_id:
            raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH)
        if not isinstance(requirement, ServiceRequirement):
            raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)

        service_matches = [
            item for item in self.registry.registered() if item.contract.service_id == requirement.service_id
        ]
        if not service_matches:
            return _human_required(ServiceBindingFailureCode.NO_BINDING_AVAILABLE)

        eligible = [
            item
            for item in service_matches
            if item.contract.interface_version == requirement.interface_version
            and set(requirement.required_features).issubset(item.contract.supported_features)
        ]
        if not eligible:
            return _human_required(ServiceBindingFailureCode.INCOMPATIBLE_BINDING)

        highest_priority = max(item.contract.priority for item in eligible)
        highest = tuple(item for item in eligible if item.contract.priority == highest_priority)
        if len(highest) != 1:
            return _human_required(ServiceBindingFailureCode.AMBIGUOUS_BINDING_SELECTION)

        selected = highest[0]
        return ServiceBindingResolution(
            status=ServiceBindingResolutionStatus.SELECTED,
            reason=None,
            binding_id=selected.contract.binding_id,
            binding_version=selected.contract.version,
            binding_digest=selected.content_digest,
            adapter_id=selected.contract.adapter_id,
            adapter_version=selected.contract.adapter_version,
            supported_features=selected.contract.supported_features,
            secret_slot_ids=selected.contract.secret_slot_ids,
        )


@dataclass(frozen=True, slots=True)
class ServiceBindingResolutionRecord:
    resolution_id: str
    project_id: str
    run_id: str
    requirement_digest: str
    service_id: str
    interface_version: str
    required_features: tuple[str, ...]
    binding_policy_digest: str
    status: ServiceBindingResolutionStatus
    reason: ServiceBindingFailureCode | None
    binding_id: str | None
    binding_version: str | None
    binding_digest: str | None
    adapter_id: str | None
    adapter_version: str | None
    supported_features: tuple[str, ...]
    secret_slot_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "resolution_id": self.resolution_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "requirement_digest": self.requirement_digest,
            "service_id": self.service_id,
            "interface_version": self.interface_version,
            "required_features": list(self.required_features),
            "binding_policy_digest": self.binding_policy_digest,
            "status": self.status.value,
            "reason": self.reason.value if self.reason is not None else None,
            "binding_id": self.binding_id,
            "binding_version": self.binding_version,
            "binding_digest": self.binding_digest,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "supported_features": list(self.supported_features),
            "secret_slot_ids": list(self.secret_slot_ids),
            "contains_raw_application_payload": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_authority": False,
        }


def record_service_binding_resolution(
    *,
    project_id: str,
    run_id: str,
    requirement: ServiceRequirement,
    policy: ServiceBindingAdmissionPolicy,
    resolution: ServiceBindingResolution,
    registered_binding: RegisteredServiceBinding | None = None,
) -> ServiceBindingResolutionRecord:
    project = _canonical_uuid(project_id)
    run = _canonical_uuid(run_id)
    if not isinstance(requirement, ServiceRequirement) or not isinstance(policy, ServiceBindingAdmissionPolicy):
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if not isinstance(resolution, ServiceBindingResolution):
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if policy.project_id != project:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)

    if resolution.selected:
        if registered_binding is None:
            raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
        _validate_selected_resolution(project, requirement, policy, resolution, registered_binding)
    elif registered_binding is not None:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)

    core: dict[str, object] = {
        "project_id": project,
        "run_id": run,
        "requirement_digest": requirement.digest,
        "service_id": requirement.service_id,
        "interface_version": requirement.interface_version,
        "required_features": list(requirement.required_features),
        "binding_policy_digest": policy.digest,
        "status": resolution.status.value,
        "reason": resolution.reason.value if resolution.reason is not None else None,
        "binding_id": resolution.binding_id,
        "binding_version": resolution.binding_version,
        "binding_digest": resolution.binding_digest,
        "adapter_id": resolution.adapter_id,
        "adapter_version": resolution.adapter_version,
        "supported_features": list(resolution.supported_features),
        "secret_slot_ids": list(resolution.secret_slot_ids),
    }
    resolution_id = f"bindingres:{sha256(_canonical_json(core)).hexdigest()}"
    return ServiceBindingResolutionRecord(
        resolution_id=resolution_id,
        project_id=project,
        run_id=run,
        requirement_digest=requirement.digest,
        service_id=requirement.service_id,
        interface_version=requirement.interface_version,
        required_features=requirement.required_features,
        binding_policy_digest=policy.digest,
        status=resolution.status,
        reason=resolution.reason,
        binding_id=resolution.binding_id,
        binding_version=resolution.binding_version,
        binding_digest=resolution.binding_digest,
        adapter_id=resolution.adapter_id,
        adapter_version=resolution.adapter_version,
        supported_features=resolution.supported_features,
        secret_slot_ids=resolution.secret_slot_ids,
    )


def public_contract_field_names() -> tuple[str, ...]:
    """Return public contract fields for structural secret/authority regression tests."""
    contract_types = (ServiceRequirement, ProjectServiceBinding, ServiceBindingResolutionRecord)
    return tuple(sorted({field.name for contract_type in contract_types for field in fields(contract_type)}))


def _validate_selected_resolution(
    project_id: str,
    requirement: ServiceRequirement,
    policy: ServiceBindingAdmissionPolicy,
    resolution: ServiceBindingResolution,
    registered: RegisteredServiceBinding,
) -> None:
    contract = registered.contract
    if contract.project_id != project_id:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if registered.admission_policy_digest != policy.digest:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if policy.approved_digest(contract.binding_id, contract.version) != registered.content_digest:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if contract.service_id != requirement.service_id or contract.interface_version != requirement.interface_version:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    if not set(requirement.required_features).issubset(contract.supported_features):
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)
    expected = (
        contract.binding_id,
        contract.version,
        registered.content_digest,
        contract.adapter_id,
        contract.adapter_version,
        contract.supported_features,
        contract.secret_slot_ids,
    )
    actual = (
        resolution.binding_id,
        resolution.binding_version,
        resolution.binding_digest,
        resolution.adapter_id,
        resolution.adapter_version,
        resolution.supported_features,
        resolution.secret_slot_ids,
    )
    if actual != expected:
        raise ServiceBindingError(ServiceBindingFailureCode.RESOLUTION_IDENTITY_MISMATCH)


def _human_required(reason: ServiceBindingFailureCode) -> ServiceBindingResolution:
    return ServiceBindingResolution(
        status=ServiceBindingResolutionStatus.HUMAN_REQUIRED,
        reason=reason,
        binding_id=None,
        binding_version=None,
        binding_digest=None,
        adapter_id=None,
        adapter_version=None,
        supported_features=(),
        secret_slot_ids=(),
    )


def _bounded_tokens(
    values: Iterable[str],
    *,
    limit: int,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    items = tuple(values)
    if len(items) > limit or (require_nonempty and not items):
        raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
    normalized = tuple(_safe_token(item) for item in items)
    if len(set(normalized)) != len(normalized):
        raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
    return tuple(sorted(normalized))


def _safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
    return value


def _semver(value: str) -> str:
    if not isinstance(value, str) or not _SEMVER_RE.fullmatch(value):
        raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
    return value


def _sha256_digest(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ServiceBindingError(ServiceBindingFailureCode.INVALID_BINDING_CONTRACT)
    return value


def _canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH) from exc
    canonical = str(parsed)
    if canonical != value:
        raise ServiceBindingError(ServiceBindingFailureCode.PROJECT_IDENTITY_MISMATCH)
    return canonical


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "AllowedAdapter",
    "ProjectServiceBinding",
    "ProjectServiceBindingRegistry",
    "RegisteredServiceBinding",
    "SERVICE_BINDING_CONTRACT_VERSION",
    "ServiceBindingAdmissionPolicy",
    "ServiceBindingApproval",
    "ServiceBindingError",
    "ServiceBindingFailureCode",
    "ServiceBindingResolution",
    "ServiceBindingResolutionRecord",
    "ServiceBindingResolutionStatus",
    "ServiceBindingResolver",
    "ServiceRequirement",
    "public_contract_field_names",
    "record_service_binding_resolution",
]
