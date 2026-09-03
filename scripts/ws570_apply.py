from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text()
    if text.count(old) != 1:
        raise SystemExit(f"expected one anchor in {path}, found {text.count(old)}")
    target.write_text(text.replace(old, new, 1))


replace_once(
    "services/api/parallax_api/code/greenfield_github.py",
    '''@dataclass(frozen=True, slots=True)\nclass GreenfieldRepositoryInspection:\n    repository_ref: str\n    default_branch: str\n    head_revision: str | None\n\n    def __post_init__(self) -> None:\n        require_repository_ref(self.repository_ref)\n        require_source_revision(self.default_branch, field="default_branch")\n        if self.head_revision is not None:\n            require_source_revision(self.head_revision, field="head_revision")\n\n    @property\n    def is_empty(self) -> bool:\n        return self.head_revision is None\n''',
    '''@dataclass(frozen=True, slots=True)\nclass GreenfieldRepositoryInspection:\n    repository_ref: str\n    default_branch: str\n    head_revision: str | None\n    head_tree_revision: str | None = None\n    head_message: str | None = None\n\n    def __post_init__(self) -> None:\n        require_repository_ref(self.repository_ref)\n        require_source_revision(self.default_branch, field="default_branch")\n        if self.head_revision is None:\n            if self.head_tree_revision is not None or self.head_message is not None:\n                raise ValueError("empty repository inspection cannot carry head metadata")\n            return\n        require_source_revision(self.head_revision, field="head_revision")\n        require_source_revision(self.head_tree_revision or "", field="head_tree_revision")\n        if not isinstance(self.head_message, str) or not self.head_message:\n            raise ValueError("commit-bearing repository inspection requires head_message")\n\n    @property\n    def is_empty(self) -> bool:\n        return self.head_revision is None\n\n    @property\n    def is_commit_bearing_empty(self) -> bool:\n        return self.head_revision is not None and self.head_tree_revision == _CANONICAL_EMPTY_TREE_SHA\n\n    @property\n    def is_canonical_baseline_candidate(self) -> bool:\n        return self.head_revision is not None and self.head_message == _CLEANUP_MESSAGE\n''',
)

replace_once(
    "services/api/parallax_api/code/greenfield_github.py",
    '''        default_branch = _text(payload.get("default_branch"))\n        head = self._default_head(repository_ref, default_branch)\n        return GreenfieldRepositoryInspection(repository_ref, default_branch, head)\n''',
    '''        default_branch = _text(payload.get("default_branch"))\n        head = self._default_head(repository_ref, default_branch)\n        if head is None:\n            return GreenfieldRepositoryInspection(repository_ref, default_branch, None)\n\n        commit = self._commit(repository_ref, head)\n        message = _text(commit.get("message"))\n        _list(commit.get("parents"))\n        tree_revision = _text(_dict(commit.get("tree")).get("sha"))\n        stable_head = self._default_head(repository_ref, default_branch)\n        if stable_head != head:\n            raise ProviderClientError("GREENFIELD_INITIALIZATION_CONFLICT")\n        return GreenfieldRepositoryInspection(\n            repository_ref,\n            default_branch,\n            head,\n            tree_revision,\n            message,\n        )\n''',
)

replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''    def deliver(self, run: EngineeringRun, *, operation_key: str) -> VerifiedDeliveryResult:\n''',
    '''    def _delivery_base(\n        self,\n        *,\n        binding,\n        delivery_key: str,\n        provenance_digest: str,\n    ) -> tuple[str, str, list[ProviderActionAuditPair]]:\n        inspected = self.greenfield.inspect_repository(\n            binding,\n            _invocation(\n                self.github_capability_id,\n                ACTION_REPOSITORY_INSPECT,\n                f"{delivery_key}:greenfield-inspect",\n            ),\n        )\n        actions: list[ProviderActionAuditPair] = [self._paired(inspected)]\n        state = inspected.value\n        if state.is_empty or state.is_canonical_baseline_candidate:\n            baseline = self.greenfield.initialize_empty_baseline(\n                binding,\n                _invocation(\n                    self.github_capability_id,\n                    ACTION_REPOSITORY_INITIALIZE_EMPTY,\n                    f"{delivery_key}:greenfield-baseline",\n                ),\n                provenance_digest=provenance_digest,\n            )\n            actions.append(self._paired(baseline))\n            return baseline.value.default_branch, baseline.value.baseline_revision, actions\n        if state.is_commit_bearing_empty:\n            if state.head_revision is None:\n                raise VerifiedDeliveryError("commit-bearing empty repository is missing its exact head")\n            return state.default_branch, state.head_revision, actions\n        raise VerifiedDeliveryError(\n            "greenfield repository default branch became non-empty before accepted-source publication"\n        )\n\n    def deliver(self, run: EngineeringRun, *, operation_key: str) -> VerifiedDeliveryResult:\n''',
)

replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''        baseline = self.greenfield.initialize_empty_baseline(\n            binding,\n            _invocation(\n                self.github_capability_id,\n                ACTION_REPOSITORY_INITIALIZE_EMPTY,\n                f"{delivery_key}:greenfield-baseline",\n            ),\n            provenance_digest=provenance_digest,\n        )\n        actions: list[ProviderActionAuditPair] = [self._paired(baseline)]\n        expected_root_digest = sha256(\n            greenfield_source_ref(binding.repository_ref, baseline.value.default_branch).encode("utf-8")\n        ).hexdigest()\n''',
    '''        base_branch, base_revision, actions = self._delivery_base(\n            binding=binding,\n            delivery_key=delivery_key,\n            provenance_digest=provenance_digest,\n        )\n        expected_root_digest = sha256(\n            greenfield_source_ref(binding.repository_ref, base_branch).encode("utf-8")\n        ).hexdigest()\n''',
)

replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''            branch_name=branch_name,\n            base_revision=baseline.value.baseline_revision,\n''',
    '''            branch_name=branch_name,\n            base_revision=base_revision,\n''',
)
replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''            branch_name=branch_name,\n            expected_parent_revision=baseline.value.baseline_revision,\n''',
    '''            branch_name=branch_name,\n            expected_parent_revision=base_revision,\n''',
)
replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''            base_branch=baseline.value.default_branch,\n''',
    '''            base_branch=base_branch,\n''',
)
replace_once(
    "services/api/parallax_api/code/greenfield_composition.py",
    '''            or read_pull_request.value.base_branch != baseline.value.default_branch\n''',
    '''            or read_pull_request.value.base_branch != base_branch\n''',
)

replace_once(
    "services/api/parallax_api/code/greenfield_delivery_upgrade.py",
    '''from .greenfield_github import (\n    ACTION_REPOSITORY_INITIALIZE_EMPTY,\n    GreenfieldGitHubActions,\n''',
    '''from .greenfield_github import (\n    ACTION_REPOSITORY_INITIALIZE_EMPTY,\n    ACTION_REPOSITORY_INSPECT,\n    GreenfieldGitHubActions,\n''',
)
replace_once(
    "services/api/parallax_api/code/greenfield_delivery_upgrade.py",
    '''                actions=(\n                    ToolActionPolicy(\n                        ACTION_REPOSITORY_INITIALIZE_EMPTY,\n                        ToolConsequence.MUTATE,\n                    ),\n                ),\n''',
    '''                actions=(\n                    ToolActionPolicy(ACTION_REPOSITORY_INSPECT, ToolConsequence.READ),\n                    ToolActionPolicy(\n                        ACTION_REPOSITORY_INITIALIZE_EMPTY,\n                        ToolConsequence.MUTATE,\n                    ),\n                ),\n''',
)

# Append focused provider-realistic inspection regressions.
test_path = Path("services/api/tests/test_greenfield_github.py")
test_text = test_path.read_text()
marker = "def test_commit_bearing_empty_inspection_is_stable_and_exact() -> None:"
if marker not in test_text:
    test_text += r'''


def test_commit_bearing_empty_inspection_is_stable_and_exact() -> None:
    head = "f" * 40
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            return httpx.Response(200, json={"object": {"sha": head}})
        if path.endswith(f"/git/commits/{head}"):
            return httpx.Response(
                200,
                json={"message": "Ordinary empty commit", "parents": [{"sha": OTHER}], "tree": {"sha": EMPTY_TREE}},
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert ref_reads == 2
    assert result.is_empty is False
    assert result.is_commit_bearing_empty is True
    assert result.is_canonical_baseline_candidate is False
    assert result.head_revision == head
    assert result.head_tree_revision == EMPTY_TREE
    assert result.head_message == "Ordinary empty commit"


def test_canonical_cleanup_message_is_preserved_as_strict_baseline_candidate() -> None:
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}], EMPTY_TREE),
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert ref_reads == 2
    assert result.is_commit_bearing_empty is True
    assert result.is_canonical_baseline_candidate is True


def test_commit_bearing_inspection_fails_closed_when_default_ref_moves() -> None:
    ref_reads = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal ref_reads
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            ref_reads += 1
            revision = BASELINE if ref_reads == 1 else OTHER
            return httpx.Response(200, json={"object": {"sha": revision}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(
                200,
                json={"message": "Ordinary empty commit", "parents": [], "tree": {"sha": EMPTY_TREE}},
            )
        raise AssertionError((request.method, request.url))

    with pytest.raises(ProviderClientError, match="GREENFIELD_INITIALIZATION_CONFLICT"):
        _client(handler).inspect_repository(REPOSITORY)


def test_commit_bearing_nonempty_inspection_remains_distinct() -> None:
    head = "f" * 40

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": head}})
        if path.endswith(f"/git/commits/{head}"):
            return httpx.Response(
                200,
                json={"message": "Repository now has source", "parents": [], "tree": {"sha": OTHER}},
            )
        raise AssertionError((request.method, request.url))

    result = _client(handler).inspect_repository(REPOSITORY)
    assert result.is_empty is False
    assert result.is_commit_bearing_empty is False
    assert result.head_tree_revision == OTHER
'''
    test_path.write_text(test_text)

# Add focused delivery-base selection tests without reconstructing the full delivery stack.
composition_test = Path("services/api/tests/test_greenfield_commit_bearing_delivery.py")
if not composition_test.exists():
    composition_test.write_text(r'''from __future__ import annotations

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
''')
