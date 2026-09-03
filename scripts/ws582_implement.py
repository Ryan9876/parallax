from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one occurrence, found {count}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


github_client = Path("services/api/parallax_api/tools/providers/github_client.py")
replace_once(
    github_client,
    """        self._http = httpx.Client(
            base_url=_GITHUB_API,
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )

    def _headers""",
    """        self._http = httpx.Client(
            base_url=_GITHUB_API,
            transport=transport,
            timeout=httpx.Timeout(float(timeout_seconds)),
            follow_redirects=False,
        )
        # One-shot acknowledgement of an exact GitHub ref mutation made by this
        # client. It bridges only the immediately following stale/absent read.
        self._ref_mutation_acknowledgements: dict[
            tuple[str, str], tuple[str | None, str]
        ] = {}

    def _headers""",
)
replace_once(
    github_client,
    """    def _get_ref(self, repository_ref: str, branch_name: str) -> str | None:
        path = f"{self._repo_path(repository_ref)}/git/ref/heads/{quote(branch_name, safe='/')}"
        response = self._send("GET", repository_ref, path)
        if response.status_code == 404:
            return None
        self._raise_status(response)
        payload = _dict(self._json(response))
        object_payload = _dict(payload.get("object"))
        return _string(object_payload.get("sha"))

    def resolve_repository""",
    """    def _get_ref(self, repository_ref: str, branch_name: str) -> str | None:
        path = f"{self._repo_path(repository_ref)}/git/ref/heads/{quote(branch_name, safe='/')}"
        response = self._send("GET", repository_ref, path)
        if response.status_code == 404:
            return None
        self._raise_status(response)
        payload = _dict(self._json(response))
        object_payload = _dict(payload.get("object"))
        return _string(object_payload.get("sha"))

    def _remember_ref_mutation(
        self,
        repository_ref: str,
        branch_name: str,
        *,
        prior_head: str | None,
        new_head: str,
    ) -> None:
        self._ref_mutation_acknowledgements[(repository_ref, branch_name)] = (
            prior_head,
            new_head,
        )

    def _get_ref_with_acknowledged_mutation(
        self,
        repository_ref: str,
        branch_name: str,
        *,
        expected_head: str,
    ) -> str | None:
        current = self._get_ref(repository_ref, branch_name)
        acknowledgement = self._ref_mutation_acknowledgements.pop(
            (repository_ref, branch_name),
            None,
        )
        if current == expected_head:
            return current
        if acknowledgement is None or acknowledgement[1] != expected_head:
            return current
        prior_head, new_head = acknowledgement
        if current is None or current == prior_head:
            return new_head
        return current

    def resolve_repository""",
)
replace_once(
    github_client,
    """    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        owner, repository = _repository_parts(repository_ref)
""",
    """    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        # Acknowledgements never cross a fresh repository-resolution boundary.
        self._ref_mutation_acknowledgements.clear()
        owner, repository = _repository_parts(repository_ref)
""",
)
replace_once(
    github_client,
    """        if returned_ref != f"refs/heads/{branch_name}" or head != base_revision:
            raise ProviderClientError("SOURCE_MISMATCH")
        return GitHubBranchResult(repository_ref, branch_name, base_revision, head)
""",
    """        if returned_ref != f"refs/heads/{branch_name}" or head != base_revision:
            raise ProviderClientError("SOURCE_MISMATCH")
        self._remember_ref_mutation(
            repository_ref,
            branch_name,
            prior_head=None,
            new_head=head,
        )
        return GitHubBranchResult(repository_ref, branch_name, base_revision, head)
""",
)
replace_once(
    github_client,
    """        current = self._get_ref(repository_ref, branch_name)
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_parent_revision:
""",
    """        current = self._get_ref_with_acknowledged_mutation(
            repository_ref,
            branch_name,
            expected_head=expected_parent_revision,
        )
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_parent_revision:
""",
)
replace_once(
    github_client,
    """        else:
            self._raise_status(ref_response, conflict="STALE_PARENT")
            final_head = self._get_ref(repository_ref, branch_name)
            if final_head != commit_revision:
                raise ProviderClientError("SOURCE_MISMATCH")

        return GitHubCommitResult(
""",
    """        else:
            self._raise_status(ref_response, conflict="STALE_PARENT")
            ref_payload = _dict(self._json(ref_response))
            returned_ref = _string(ref_payload.get("ref"))
            object_payload = _dict(ref_payload.get("object"))
            returned_head = _string(object_payload.get("sha"))
            if (
                returned_ref != f"refs/heads/{branch_name}"
                or returned_head != commit_revision
            ):
                raise ProviderClientError("SOURCE_MISMATCH")
            self._remember_ref_mutation(
                repository_ref,
                branch_name,
                prior_head=expected_parent_revision,
                new_head=commit_revision,
            )

        return GitHubCommitResult(
""",
)
replace_once(
    github_client,
    """        current = self._get_ref(repository_ref, head_branch)
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_head_revision:
""",
    """        current = self._get_ref_with_acknowledged_mutation(
            repository_ref,
            head_branch,
            expected_head=expected_head_revision,
        )
        if current is None:
            raise ProviderClientError("BRANCH_NOT_FOUND")
        if current != expected_head_revision:
""",
)


source = Path("services/api/parallax_api/code/source_delivery_composition.py")
replace_once(
    source,
    """    ProviderActionEvidence,
    ProviderActionState,
""",
    """    ProviderActionEvidence,
    ProviderActionFailed,
    ProviderActionState,
""",
)
replace_once(
    source,
    """    def _invocation(self, tool: str, action: str, operation_key: str) -> ProviderInvocation:
        return self.invocations.for_action(tool=tool, action=action, operation_key=operation_key)

    @staticmethod
    def _paired""",
    """    def _invocation(self, tool: str, action: str, operation_key: str) -> ProviderInvocation:
        return self.invocations.for_action(tool=tool, action=action, operation_key=operation_key)

    @staticmethod
    def _provider_failure_code(error: ProviderActionFailed) -> str | None:
        code = error.audit.result_code or error.evidence.result_status
        return code if isinstance(code, str) and code else None

    def _publish_branch_commit(
        self,
        *,
        binding: ProviderProjectBinding,
        delivery_key: str,
        branch_name: str,
        base_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
        actions: list[ProviderActionAuditPair],
    ):
        try:
            branch = self.github.create_branch(
                binding,
                self._invocation(
                    GITHUB_TOOL,
                    ACTION_BRANCH_CREATE,
                    f"{delivery_key}:branch",
                ),
                branch_name=branch_name,
                base_revision=base_revision,
            )
        except ProviderActionFailed as exc:
            if self._provider_failure_code(exc) != "BRANCH_CONFLICT":
                raise
            # A previous partial attempt may already have advanced the exact
            # canonical branch. The existing commit action remains the only
            # authority allowed to prove that head is the exact accepted
            # Parallax lineage commit with the exact expected parent.
        else:
            actions.append(self._paired(branch))

        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(
                GITHUB_TOOL,
                ACTION_COMMIT_WRITE,
                f"{delivery_key}:commit",
            ),
            branch_name=branch_name,
            expected_parent_revision=base_revision,
            lineage=lineage,
            files=files,
        )
        actions.append(self._paired(commit))
        return commit

    @staticmethod
    def _paired""",
)
replace_once(
    source,
    """        branch = self.github.create_branch(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_BRANCH_CREATE, f"{delivery_key}:branch"),
            branch_name=branch_name,
            base_revision=repository.value.head_revision,
        )
        actions.append(self._paired(branch))
        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_COMMIT_WRITE, f"{delivery_key}:commit"),
            branch_name=branch_name,
            expected_parent_revision=repository.value.head_revision,
            lineage=lineage,
            files=files,
        )
        actions.append(self._paired(commit))
""",
    """        commit = self._publish_branch_commit(
            binding=binding,
            delivery_key=delivery_key,
            branch_name=branch_name,
            base_revision=repository.value.head_revision,
            lineage=lineage,
            files=files,
            actions=actions,
        )
""",
)


greenfield = Path("services/api/parallax_api/code/greenfield_composition.py")
replace_once(
    greenfield,
    """        branch = self.github.create_branch(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_BRANCH_CREATE, f"{delivery_key}:branch"),
            branch_name=branch_name,
            base_revision=base_revision,
        )
        actions.append(self._paired(branch))
        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_COMMIT_WRITE, f"{delivery_key}:commit"),
            branch_name=branch_name,
            expected_parent_revision=base_revision,
            lineage=lineage,
            files=files,
        )
        actions.append(self._paired(commit))
""",
    """        commit = self._publish_branch_commit(
            binding=binding,
            delivery_key=delivery_key,
            branch_name=branch_name,
            base_revision=base_revision,
            lineage=lineage,
            files=files,
            actions=actions,
        )
""",
)


provider_tests = Path("services/api/tests/test_provider_clients.py")
with provider_tests.open("a", encoding="utf-8") as handle:
    handle.write(r'''

OTHER_HEAD = "9" * 40


class GitHubStaleRefTransport(GitHubHappyTransport):
    def __init__(
        self,
        *,
        stale_after_patch_reads: int = 1,
        unexpected_after_patch: bool = False,
    ) -> None:
        super().__init__()
        self.branch_ref_reads = 0
        self.stale_after_patch_reads = stale_after_patch_reads
        self.unexpected_after_patch = unexpected_after_patch

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        branch_path = "/repos/acme/example-app/git/ref/heads/parallax/run-1"
        if request.method == "GET" and path == branch_path:
            self.branch_ref_reads += 1
            if self.branch_ref_reads == 2:
                # GitHub acknowledged branch creation but the exact ref is not
                # visible to the immediately following commit-stage read.
                return httpx.Response(404, json={"message": "not found"})
            if self.branch_ref_reads >= 3:
                if self.unexpected_after_patch and self.branch_ref_reads == 3:
                    return httpx.Response(200, json=self._ref(OTHER_HEAD, "parallax/run-1"))
                if self.branch_ref_reads < 3 + self.stale_after_patch_reads:
                    # GitHub acknowledged the non-force PATCH but this read
                    # still returns the exact prior branch head.
                    return httpx.Response(200, json=self._ref(BASE, "parallax/run-1"))
        return super().__call__(request)


def _commit_file() -> GitHubCommitFile:
    content = "print('updated')\n"
    return GitHubCommitFile(
        "src/app.py",
        content,
        __import__("hashlib").sha256(content.encode()).hexdigest(),
    )


def test_github_ref_mutation_acknowledgements_bridge_only_immediate_stale_reads() -> None:
    handler = GitHubStaleRefTransport(stale_after_patch_reads=2)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    assert client.resolve_repository(REPOSITORY_REF).head_revision == BASE
    assert client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE).head_revision == BASE
    commit = client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )
    assert commit.commit_revision == COMMIT

    created = client.create_pull_request(
        REPOSITORY_REF,
        "parallax/run-1",
        COMMIT,
        "main",
        "Parallax change",
        "bounded body",
    )
    assert created.number == 42

    # The acknowledgement was consumed by the first stale read. A second
    # identical stale provider view cannot inherit or replay that authority.
    with pytest.raises(ProviderClientError, match="STALE_HEAD"):
        client.create_pull_request(
            REPOSITORY_REF,
            "parallax/run-1",
            COMMIT,
            "main",
            "Parallax change",
            "bounded body",
        )


def test_github_ref_mutation_acknowledgement_never_masks_unexpected_head() -> None:
    handler = GitHubStaleRefTransport(unexpected_after_patch=True)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    assert client.resolve_repository(REPOSITORY_REF).head_revision == BASE
    client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    client.commit_files(
        REPOSITORY_REF,
        "parallax/run-1",
        BASE,
        LINEAGE,
        (_commit_file(),),
    )

    with pytest.raises(ProviderClientError, match="STALE_HEAD"):
        client.create_pull_request(
            REPOSITORY_REF,
            "parallax/run-1",
            COMMIT,
            "main",
            "Parallax change",
            "bounded body",
        )
    assert handler.pull_posts == 0


def test_github_ref_mutation_acknowledgements_do_not_cross_repository_resolution() -> None:
    handler = GitHubStaleRefTransport(stale_after_patch_reads=2)
    client = GitHubRestProviderClient(
        GitHubCredentials(),
        transport=httpx.MockTransport(handler),
    )

    client.resolve_repository(REPOSITORY_REF)
    client.create_branch(REPOSITORY_REF, "parallax/run-1", BASE)
    # A fresh repository resolution is the delivery-sequence boundary and
    # discards the one-shot branch-create acknowledgement.
    client.resolve_repository(REPOSITORY_REF)
    with pytest.raises(ProviderClientError, match="BRANCH_NOT_FOUND"):
        client.commit_files(
            REPOSITORY_REF,
            "parallax/run-1",
            BASE,
            LINEAGE,
            (_commit_file(),),
        )
''')


source_tests = Path("services/api/tests/test_source_delivery_composition.py")
replace_once(
    source_tests,
    """    ProviderActionEvidence,
    ProviderActionState,
""",
    """    ProviderActionEvidence,
    ProviderActionFailed,
    ProviderActionState,
""",
)
replace_once(
    source_tests,
    """class MemoryDeliveryRecordStore:
""",
    """def _action_failure(
    binding: ProviderProjectBinding,
    *,
    provider: str,
    action: str,
    result_code: str,
    source_revision: str | None = None,
    result_identity: str | None = None,
) -> ProviderActionFailed:
    evidence = ProviderActionEvidence(
        provider=provider,
        action=action,
        state=ProviderActionState.FAILED,
        project_ref=binding.project_ref,
        repository_identity_digest=binding.repository_identity_digest,
        source_revision=source_revision,
        result_identity=result_identity,
        result_status=result_code,
    )
    request_id = f"request:{uuid4().hex}"
    audit = ToolAuditRecord(
        request_id=request_id,
        capability_id=f"cap:test-{provider}",
        project_ref=binding.project_ref,
        tool=provider,
        action=action,
        actor_ref="actor:test-runtime",
        consequence=ToolConsequence.MUTATE,
        authority_allowed=True,
        outcome=ToolOutcome.FAILED,
        deny_reason=None,
        approval_id=None,
        request_digest=sha256(f"{request_id}|{provider}|{action}".encode()).hexdigest(),
        result_digest=sha256(f"{result_code}|{result_identity or ''}".encode()).hexdigest(),
        result_code=result_code,
        result_identity=result_identity,
    )
    return ProviderActionFailed(evidence=evidence, audit=audit)


class MemoryDeliveryRecordStore:
""",
)
with source_tests.open("a", encoding="utf-8") as handle:
    handle.write(r'''

class BranchConflictReplayGitHubActions(FakeGitHubActions):
    def create_branch(self, binding, invocation, *, branch_name, base_revision):
        self.calls.append("branch.create")
        assert base_revision == ROOT_REVISION
        self.last_branch = branch_name
        raise _action_failure(
            binding,
            provider="github",
            action="branch.create",
            result_code="BRANCH_CONFLICT",
            source_revision=base_revision,
            result_identity=branch_name,
        )


class BranchConflictMismatchGitHubActions(BranchConflictReplayGitHubActions):
    def commit_accepted_lineage(
        self,
        binding,
        invocation,
        *,
        branch_name,
        expected_parent_revision,
        lineage,
        files,
    ):
        self.calls.append("commit.write")
        raise _action_failure(
            binding,
            provider="github",
            action="commit.write",
            result_code="STALE_PARENT",
            source_revision=expected_parent_revision,
            result_identity=branch_name,
        )


def test_exact_partial_commit_recovers_after_branch_conflict_without_relabeling_failure() -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = BranchConflictReplayGitHubActions(binding)
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path := __import__("pathlib").Path(pytest.ensuretemp("partial-replay")),
        project_id,
        run_id,
        github=github,
    )
    bootstrap.ensure(run, operation_key="bootstrap")
    identity = ProjectRunIdentity(project_id, run_id)
    accepted = _accept_implementation(allocator, identity)
    records = MemoryDeliveryRecordStore()
    delivery = _delivery(
        allocator,
        binding,
        github,
        FakeVercelActions(),
        project_id,
        records=records,
    )

    result = delivery.deliver(
        _review_run(project_id, run_id, accepted),
        operation_key="deliver:partial-replay",
    )

    assert result.lineage_id == accepted.lineage_id
    assert result.branch_name == publication_branch_name(identity, accepted.lineage_id)
    successful_actions = tuple(pair.evidence.action for pair in result.actions)
    assert "branch.create" not in successful_actions
    assert "commit.write" in successful_actions
    assert "pull_request.create" in successful_actions
    assert "preview.create" in successful_actions
    assert records.load(run_id=run_id, lineage_id=accepted.lineage_id) is not None


def test_arbitrary_partial_branch_head_remains_fail_closed(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    binding = ProviderProjectBinding(project_id, REPOSITORY_REF)
    github = BranchConflictMismatchGitHubActions(binding)
    bootstrap, allocator, _, github, run, _, _, binding = _bootstrap(
        tmp_path,
        project_id,
        run_id,
        github=github,
    )
    bootstrap.ensure(run, operation_key="bootstrap")
    identity = ProjectRunIdentity(project_id, run_id)
    accepted = _accept_implementation(allocator, identity)
    vercel = FakeVercelActions()
    delivery = _delivery(allocator, binding, github, vercel, project_id)

    with pytest.raises(ProviderActionFailed) as failed:
        delivery.deliver(
            _review_run(project_id, run_id, accepted),
            operation_key="deliver:partial-mismatch",
        )
    assert failed.value.audit.result_code == "STALE_PARENT"
    assert vercel.calls == []
''')


greenfield_tests = Path("services/api/tests/test_greenfield_commit_bearing_delivery.py")
replace_once(
    greenfield_tests,
    """from parallax_api.code.source_delivery_composition import VerifiedDeliveryError
""",
    """from parallax_api.code.source_delivery_composition import VerifiedDeliveryError, VerifiedLineageDelivery
""",
)
with greenfield_tests.open("a", encoding="utf-8") as handle:
    handle.write(r'''


def test_greenfield_delivery_uses_shared_partial_publication_recovery_helper() -> None:
    assert (
        GreenfieldVerifiedLineageDelivery._publish_branch_commit
        is VerifiedLineageDelivery._publish_branch_commit
    )
    import inspect

    assert "_publish_branch_commit(" in inspect.getsource(
        GreenfieldVerifiedLineageDelivery.deliver
    )
''')
