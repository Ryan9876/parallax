from __future__ import annotations

from types import SimpleNamespace

import pytest

from parallax_api.code.greenfield_composition import GreenfieldVerifiedLineageDelivery
from parallax_api.code.greenfield_github import GreenfieldRepositoryInspection
from parallax_api.code.source_delivery_composition import VerifiedDeliveryError


REPOSITORY = "github:Ryan9876/empty-target"
PROJECT = "project-1"
HEAD = "f" * 40
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PROVENANCE = "d" * 64


class _Greenfield:
    def __init__(self, inspection: GreenfieldRepositoryInspection, baseline=None):
        self.inspection = inspection
        self.baseline = baseline
        self.calls: list[str] = []

    def inspect_repository(self, binding, invocation):
        self.calls.append("inspect")
        return SimpleNamespace(value=self.inspection, evidence="inspect-evidence", audit="inspect-audit")

    def initialize_empty_baseline(self, binding, invocation, *, provenance_digest):
        self.calls.append("initialize")
        assert provenance_digest == PROVENANCE
        if self.baseline is None:
            raise AssertionError("initializer must not be called")
        return SimpleNamespace(value=self.baseline, evidence="baseline-evidence", audit="baseline-audit")


def _delivery(greenfield: _Greenfield):
    delivery = object.__new__(GreenfieldVerifiedLineageDelivery)
    delivery.greenfield = greenfield
    delivery.github_capability_id = "cap:greenfield"
    delivery._paired = lambda action: action
    return delivery


def _binding():
    return SimpleNamespace(project_ref=PROJECT, repository_ref=REPOSITORY)


def test_commit_bearing_empty_uses_exact_head_without_initializer() -> None:
    inspection = GreenfieldRepositoryInspection(
        REPOSITORY,
        "main",
        HEAD,
        EMPTY_TREE,
        "Ordinary empty commit",
    )
    greenfield = _Greenfield(inspection)
    branch, revision, actions = _delivery(greenfield)._delivery_base(
        binding=_binding(), delivery_key="delivery-key", provenance_digest=PROVENANCE
    )
    assert (branch, revision) == ("main", HEAD)
    assert greenfield.calls == ["inspect"]
    assert len(actions) == 1


def test_commit_bearing_nonempty_fails_before_initializer() -> None:
    inspection = GreenfieldRepositoryInspection(
        REPOSITORY,
        "main",
        HEAD,
        "9" * 40,
        "Repository now has source",
    )
    greenfield = _Greenfield(inspection)
    with pytest.raises(VerifiedDeliveryError, match="became non-empty"):
        _delivery(greenfield)._delivery_base(
            binding=_binding(), delivery_key="delivery-key", provenance_digest=PROVENANCE
        )
    assert greenfield.calls == ["inspect"]


def test_canonical_looking_empty_head_still_requires_strict_initializer_replay() -> None:
    inspection = GreenfieldRepositoryInspection(
        REPOSITORY,
        "main",
        HEAD,
        EMPTY_TREE,
        "Finalize Parallax empty greenfield baseline",
    )
    baseline = SimpleNamespace(default_branch="main", baseline_revision=HEAD)
    greenfield = _Greenfield(inspection, baseline)
    branch, revision, actions = _delivery(greenfield)._delivery_base(
        binding=_binding(), delivery_key="delivery-key", provenance_digest=PROVENANCE
    )
    assert (branch, revision) == ("main", HEAD)
    assert greenfield.calls == ["inspect", "initialize"]
    assert len(actions) == 2


def test_true_empty_still_requires_initializer() -> None:
    inspection = GreenfieldRepositoryInspection(REPOSITORY, "main", None)
    baseline = SimpleNamespace(default_branch="main", baseline_revision=HEAD)
    greenfield = _Greenfield(inspection, baseline)
    branch, revision, actions = _delivery(greenfield)._delivery_base(
        binding=_binding(), delivery_key="delivery-key", provenance_digest=PROVENANCE
    )
    assert (branch, revision) == ("main", HEAD)
    assert greenfield.calls == ["inspect", "initialize"]
    assert len(actions) == 2
