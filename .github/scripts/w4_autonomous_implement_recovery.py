from pathlib import Path


def replace(path: str, old: str, new: str, *, count: int = 1) -> None:
    target = Path(path)
    text = target.read_text()
    if old not in text:
        raise SystemExit(f"anchor missing in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, count))


# 1. Server-owned Project capability context. This is deliberately bounded to
# canonical IDs/refs and contains no credentials, local paths, source contents,
# provider payloads, or execution authority.
Path("services/api/parallax_api/intelligence/project_context.py").write_text('''from __future__ import annotations

MAX_PROJECT_CONTEXT_FIELD = 300


def _bounded(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    clean = value.strip()
    if not clean or clean != value or len(clean) > MAX_PROJECT_CONTEXT_FIELD:
        raise ValueError(f"{name} is invalid")
    if any(ord(ch) < 32 for ch in clean):
        raise ValueError(f"{name} contains control characters")
    return clean


def compose_project_capability_context(*, project_id: str, repository_ref: str | None) -> str:
    project = _bounded(project_id, "project_id")
    lines = [f"CANONICAL_PROJECT_ID: {project}"]
    if repository_ref is None:
        lines.extend([
            "CANONICAL_REPOSITORY_REF: UNBOUND",
            "PROTECTED_SOURCE_BOOTSTRAP: NOT_REGISTERED",
        ])
        return "\\n".join(lines)

    repository = _bounded(repository_ref, "repository_ref")
    lines.extend([
        f"CANONICAL_REPOSITORY_REF: {repository}",
        "PROTECTED_SOURCE_BOOTSTRAP: REGISTERED_FOR_BOUND_REPOSITORY",
        (
            "PROJECT_CAPABILITY_RULE: The protected Engineering Run runtime is authorized to attempt "
            "server-owned source bootstrap for this bound repository. Absence of source files from the "
            "conversation is not evidence that the repository is inaccessible and does not, by itself, "
            "require the user to upload repository files."
        ),
    ])
    return "\\n".join(lines)
''')

# 2. Bound Project facts become protected response context.
replace(
    "services/api/parallax_api/intelligence/context.py",
    "    prior_messages: Iterable[MessageLike],\n    limits: ContextLimits | None = None,\n",
    "    prior_messages: Iterable[MessageLike],\n    project_context: str | None = None,\n    limits: ContextLimits | None = None,\n",
)
replace(
    "services/api/parallax_api/intelligence/context.py",
    '''    header = [\n        f"CONVERSATION_ID: {conversation_id}",\n        f"ACTIVE_SPEC_ID: {spec_id}",\n        f"LIFECYCLE_STATUS: {status}",\n        f"MODE: {mode}",\n        AUTHORITY_RULE,\n        "PRIOR_MESSAGES:",\n    ]\n''',
    '''    header = [\n        f"CONVERSATION_ID: {conversation_id}",\n        f"ACTIVE_SPEC_ID: {spec_id}",\n        f"LIFECYCLE_STATUS: {status}",\n        f"MODE: {mode}",\n        AUTHORITY_RULE,\n    ]\n    if project_context is not None:\n        protected_project = project_context.strip()\n        if not protected_project or len(protected_project) > 1_200:\n            raise ContextLimitError("server Project context exceeds protected limits")\n        header.extend(["PROJECT_CONTEXT:", f"[SERVER AUTHORITATIVE] {protected_project}"])\n    header.append("PRIOR_MESSAGES:")\n''',
)

# Conversation service already owns ProjectRepository and authorization.
replace(
    "services/api/parallax_api/services/conversations.py",
    '''    def create(self, mode: str, project_id: str | None = None):\n''',
    '''    def project_for_conversation(self, conversation):\n        if conversation.project_id is None:\n            return None\n        return self._resolve_project(conversation.project_id)\n\n    def create(self, mode: str, project_id: str | None = None):\n''',
)

replace(
    "services/api/parallax_api/routes/conversations.py",
    "from ..intelligence.context import ContextLimitError, compose_reason_context\n",
    "from ..intelligence.context import ContextLimitError, compose_reason_context\nfrom ..intelligence.project_context import compose_project_capability_context\n",
)
replace(
    "services/api/parallax_api/routes/conversations.py",
    '''            context = compose_reason_context(\n                conversation_id=conversation.id,\n                spec_id=conversation.spec_id,\n                status=conversation.status,\n                mode=conversation.mode,\n                current_user_turn=payload.content,\n                prior_messages=prior_messages,\n            )\n''',
    '''            project_context = None\n            if conversation.mode == "code" and conversation.project_id:\n                project = svc.project_for_conversation(conversation)\n                if project is not None:\n                    project_context = compose_project_capability_context(\n                        project_id=project.id,\n                        repository_ref=project.repository_ref,\n                    )\n            context = compose_reason_context(\n                conversation_id=conversation.id,\n                spec_id=conversation.spec_id,\n                status=conversation.status,\n                mode=conversation.mode,\n                current_user_turn=payload.content,\n                prior_messages=prior_messages,\n                project_context=project_context,\n            )\n''',
)

# 3. Work Specification drafting gets the same server-owned Project facts.
replace(
    "services/api/parallax_api/services/work_specifications.py",
    "from ..intelligence.work_specification import WorkSpecificationDraft\n",
    "from ..intelligence.work_specification import WorkSpecificationDraft\nfrom ..projects.repository import ProjectRepository\n",
)
replace(
    "services/api/parallax_api/services/work_specifications.py",
    '''        conversations: ConversationRepository,\n        *,\n        owner_subject: str | None = None,\n    ):\n        self.repository = repository\n        self.conversations = conversations\n        self.owner_subject = owner_subject.strip() if owner_subject else None\n''',
    '''        conversations: ConversationRepository,\n        project_repository: ProjectRepository | None = None,\n        *,\n        owner_subject: str | None = None,\n    ):\n        self.repository = repository\n        self.conversations = conversations\n        self.projects = project_repository\n        self.owner_subject = owner_subject.strip() if owner_subject else None\n''',
)
replace(
    "services/api/parallax_api/services/work_specifications.py",
    '''    def latest(self, conversation_id: str):\n''',
    '''    def project_for_conversation(self, conversation):\n        if conversation.project_id is None:\n            return None\n        if self.projects is None or not self.owner_subject:\n            return None\n        return self.projects.get_for_owner(conversation.project_id, self.owner_subject)\n\n    def latest(self, conversation_id: str):\n''',
)

replace(
    "services/api/parallax_api/routes/work_specifications.py",
    "from ..models import WorkSpecification\n",
    "from ..models import WorkSpecification\nfrom ..intelligence.project_context import compose_project_capability_context\nfrom ..projects.repository import ProjectRepository\n",
)
replace(
    "services/api/parallax_api/routes/work_specifications.py",
    '''        WorkSpecificationRepository(session),\n        ConversationRepository(session),\n        owner_subject=principal.subject,\n''',
    '''        WorkSpecificationRepository(session),\n        ConversationRepository(session),\n        ProjectRepository(session),\n        owner_subject=principal.subject,\n''',
)
replace(
    "services/api/parallax_api/routes/work_specifications.py",
    '''    try:\n        generated = await spec_coordinator.draft(conversation.messages)\n''',
    '''    project_context = None\n    if getattr(conversation, "mode", None) == "code" and getattr(conversation, "project_id", None):\n        project = svc.project_for_conversation(conversation)\n        if project is not None:\n            project_context = compose_project_capability_context(\n                project_id=project.id,\n                repository_ref=project.repository_ref,\n            )\n    try:\n        generated = await spec_coordinator.draft(\n            conversation.messages,\n            project_context=project_context,\n        )\n''',
)

replace(
    "services/api/parallax_api/intelligence/work_specification.py",
    '    version = "work-spec-v0.7.0"\n',
    '    version = "work-spec-v0.7.1"\n',
)
replace(
    "services/api/parallax_api/intelligence/work_specification.py",
    '''            Preserve the user's actual outcome and later corrections. Do not invent approval, deployment state,\n            secret values, hidden reasoning, or requirements unsupported by the conversation. Acceptance criteria\n            must be concrete and testable. Put unresolved material gaps in open_questions instead of guessing.\n''',
    '''            Preserve the user's actual outcome and later corrections. Server-authoritative Project capability\n            facts describe what the protected runtime can access and override conflicting assistant assumptions about\n            repository availability; they do not override user outcome or substantive constraints. Do not invent\n            approval, deployment state, secret values, hidden reasoning, or requirements unsupported by the\n            conversation. Acceptance criteria must be concrete and testable. Put unresolved material gaps in\n            open_questions instead of guessing.\n''',
)
replace(
    "services/api/parallax_api/intelligence/work_specification.py",
    '''    def conversation_context(messages) -> tuple[str, str]:\n''',
    '''    def conversation_context(messages, *, project_context: str | None = None) -> tuple[str, str]:\n''',
)
replace(
    "services/api/parallax_api/intelligence/work_specification.py",
    '''        lines.reverse()\n        return objective[:6_000], "\\n\\n".join(lines)\n\n    async def draft(self, messages) -> WorkSpecificationGeneration:\n        objective, context = self.conversation_context(messages)\n''',
    '''        lines.reverse()\n        context = "\\n\\n".join(lines)\n        if project_context is not None:\n            protected = project_context.strip()\n            if not protected or len(protected) > 1_200:\n                raise ValueError("server Project context exceeds protected limits")\n            context = f"SERVER_PROJECT_CONTEXT:\\n[SERVER AUTHORITATIVE] {protected}\\n\\n{context}"\n        return objective[:6_000], context\n\n    async def draft(self, messages, *, project_context: str | None = None) -> WorkSpecificationGeneration:\n        objective, context = self.conversation_context(messages, project_context=project_context)\n''',
)

# 4. Model-visible source context explicitly satisfies file-provision preconditions.
replace(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    'MAX_GENERATED_DIFF_CHARS = 120_000\n',
    '''MAX_GENERATED_DIFF_CHARS = 120_000\nSOURCE_CONTEXT_AUTHORITY_RULE = (\n    "The current source files were supplied by the protected server-owned runtime. Any earlier statement whose "\n    "only precondition is that the repository or relevant files must be provided is satisfied by this non-empty "\n    "protected source context. Do not refuse solely because source was absent from conversational context. All "\n    "substantive Work Specification constraints and acceptance criteria remain authoritative."\n)\n''',
)
replace(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '''    def contract_payload(self) -> dict[str, object]:\n        return {\n''',
    '''    def source_prompt_payload(self) -> dict[str, object]:\n        payload = self.source_context.prompt_payload()\n        if self.source_context.files:\n            payload["runtime_source_access"] = "SERVER_PROVIDED_PROTECTED_SOURCE"\n            payload["runtime_source_authority_rule"] = SOURCE_CONTEXT_AUTHORITY_RULE\n        return payload\n\n    def contract_payload(self) -> dict[str, object]:\n        return {\n''',
)
replace(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '    version = "implementation-generation-v0.15.3"\n',
    '    version = "implementation-generation-v0.15.4"\n',
)
replace(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    '''            Patch paths and expected SHA-256 values must come from source context, except a new file may bind to\n            the SHA-256 of empty content. Never output commands, filesystem roots, URLs, credentials, environment\n            values, Git/deployment actions, approval claims, hidden reasoning, scratchpads, or extra authority.\n''',
    '''            Patch paths and expected SHA-256 values must come from source context, except a new file may bind to\n            the SHA-256 of empty content. When source context declares SERVER_PROVIDED_PROTECTED_SOURCE, treat an\n            earlier repository/file-provision precondition as satisfied by that current context; do not relax any\n            substantive constraint or acceptance criterion. Never output commands, filesystem roots, URLs,\n            credentials, environment values, Git/deployment actions, approval claims, hidden reasoning, scratchpads,\n            or extra authority.\n''',
)
replace(
    "services/api/parallax_api/intelligence/implementation_generation.py",
    "        source_json = json.dumps(request.source_context.prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(\",\", \":\"))\n",
    "        source_json = json.dumps(request.source_prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(\",\", \":\"))\n",
)

# 5. Pre-mutation IMPLEMENT failure becomes durable FAILED evidence instead of a silent active run.
replace(
    "services/api/parallax_api/code/autonomy.py",
    '''                except ImplementationRuntimeError as exc:\n                    steps.append(\n                        AutonomyStep(\n                            stage=stage.value,\n                            outcome="FAILED_AFTER_MUTATION" if exc.mutation_applied else "FAILED",\n                            tool_id="implementation-runtime",\n                        )\n                    )\n                    return AutonomyResult(\n                        run=self.service.get(run.id),\n                        stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,\n                        steps=tuple(steps),\n                    )\n''',
    '''                except ImplementationRuntimeError as exc:\n                    if exc.mutation_applied:\n                        steps.append(\n                            AutonomyStep(\n                                stage=stage.value,\n                                outcome="FAILED_AFTER_MUTATION",\n                                tool_id="implementation-runtime",\n                            )\n                        )\n                        return AutonomyResult(\n                            run=self.service.get(run.id),\n                            stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,\n                            steps=tuple(steps),\n                        )\n                    failed = self.service.complete_stage(\n                        run_id=run.id,\n                        stage=WorkflowStage.IMPLEMENT,\n                        operation_key=stage_key,\n                        expected_revision=run.revision,\n                        passed=False,\n                        evidence={\n                            "error_class": type(exc).__name__,\n                            "mutation_applied": False,\n                        },\n                        failure_code="AUTONOMOUS_IMPLEMENT_FAILED",\n                        program_id="protected-implementation-runtime-v0.15.4",\n                        tool_id="safe-source-implementation-v1",\n                    )\n                    steps.append(\n                        AutonomyStep(\n                            stage=stage.value,\n                            outcome="FAILED",\n                            attempt_id=failed.attempt_id,\n                            replayed=failed.replayed,\n                            tool_id="implementation-runtime",\n                        )\n                    )\n                    return AutonomyResult(\n                        run=failed.run,\n                        stop_reason=AutonomyStopReason.IMPLEMENTATION_FAILED,\n                        steps=tuple(steps),\n                    )\n''',
)

replace(
    "services/api/parallax_api/code/service.py",
    '''        for key in ("lineage_bound_execution", "timed_out", "redacted"):\n''',
    '''        for key in ("lineage_bound_execution", "timed_out", "redacted", "mutation_applied"):\n''',
)
replace(
    "services/api/parallax_api/code/service.py",
    '''        value = evidence.get("exit_code")\n''',
    '''        error_class = evidence.get("error_class")\n        if isinstance(error_class, str) and len(error_class) <= 80 and error_class.isidentifier():\n            metadata["error_class"] = error_class\n        value = evidence.get("exit_code")\n''',
)

# 6. Client can continue IMPLEMENT through the protected autonomous route.
replace(
    "apps/client/src/hooks/useEngineeringRun.ts",
    "const AUTONOMOUS_STAGES = new Set(['PLAN', 'BUILD', 'TEST', 'VERIFY']);\n",
    "const AUTONOMOUS_STAGES = new Set(['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY']);\n",
)
replace(
    "apps/client/src/components/EngineeringRunStatus.tsx",
    "const AUTONOMOUS_STAGES = ['PLAN', 'BUILD', 'TEST', 'VERIFY'];\n",
    "const AUTONOMOUS_STAGES = ['PLAN', 'IMPLEMENT', 'BUILD', 'TEST', 'VERIFY'];\n",
)
replace(
    "apps/client/src/components/EngineeringRunStatus.tsx",
    "    IMPLEMENTATION_REQUIRED: 'Autonomy boundary · implementation evidence required',\n",
    "    IMPLEMENTATION_REQUIRED: 'Autonomy boundary · protected implementation can continue here',\n    IMPLEMENTATION_FAILED: 'Autonomy stopped · protected implementation failed before acceptance; review the recorded failure and resume explicitly',\n",
)

# 7. Regression tests for server Project context.
replace(
    "services/api/tests/test_reason_context_scope.py",
    '''from parallax_api.intelligence.protected_metrics import evaluate_reason_result, evaluate_scope_output\n''',
    '''from parallax_api.intelligence.project_context import compose_project_capability_context\nfrom parallax_api.intelligence.protected_metrics import evaluate_reason_result, evaluate_scope_output\n''',
)
with Path("services/api/tests/test_reason_context_scope.py").open("a") as handle:
    handle.write('''\n\ndef test_project_bound_code_context_overrides_false_assistant_repository_assumption():\n    project_context = compose_project_capability_context(\n        project_id="project-1",\n        repository_ref="github:ryan9876/parallax",\n    )\n    bundle = compose_reason_context(\n        conversation_id="conversation-code",\n        spec_id="P2-V0.17.5",\n        status="ACTIVE",\n        mode="code",\n        current_user_turn="Animate the Parallax logo.",\n        prior_messages=[\n            message("assistant", "I do not have access to the repository; upload its files."),\n        ],\n        project_context=project_context,\n    )\n    assert "[SERVER AUTHORITATIVE]" in bundle.text\n    assert "github:ryan9876/parallax" in bundle.text\n    assert "REGISTERED_FOR_BOUND_REPOSITORY" in bundle.text\n    assert "[ASSISTANT CONTEXT_ONLY] I do not have access" in bundle.text\n    assert "does not, by itself, require the user to upload repository files" in bundle.text\n''')

replace(
    "services/api/tests/test_work_specifications.py",
    '''from parallax_api.intelligence.work_specification import (\n''',
    '''from parallax_api.intelligence.project_context import compose_project_capability_context\nfrom parallax_api.intelligence.work_specification import (\n''',
)
with Path("services/api/tests/test_work_specifications.py").open("a") as handle:
    handle.write('''\n\ndef test_work_spec_context_includes_server_authoritative_project_capability():\n    coordinator = WorkSpecificationCoordinator()\n    messages = [\n        SimpleNamespace(role="user", content="Animate the Parallax logo."),\n        SimpleNamespace(role="assistant", content="I cannot access the repository; upload the files."),\n    ]\n    project_context = compose_project_capability_context(\n        project_id="project-1",\n        repository_ref="github:ryan9876/parallax",\n    )\n    objective, context = coordinator.conversation_context(messages, project_context=project_context)\n    assert objective == "Animate the Parallax logo."\n    assert context.startswith("SERVER_PROJECT_CONTEXT:\\n[SERVER AUTHORITATIVE]")\n    assert "github:ryan9876/parallax" in context\n    assert "ASSISTANT: I cannot access the repository" in context\n''')

# Update the route fake to accept the now-bounded optional keyword.
replace(
    "services/api/tests/test_work_specifications.py",
    '''        async def draft(self, messages):\n''',
    '''        async def draft(self, messages, *, project_context=None):\n            assert project_context is None\n''',
)

# 8. Regression tests for durable IMPLEMENT failure semantics.
replace(
    "services/api/tests/test_code_autonomy.py",
    "from parallax_api.code.execution import ExecutionPolicyError, ExecutionSpec\n",
    "from parallax_api.code.execution import ExecutionPolicyError, ExecutionSpec\nfrom parallax_api.code.implementation_runtime import ImplementationRuntimeError\n",
)
with Path("services/api/tests/test_code_autonomy.py").open("a") as handle:
    handle.write('''\n\nclass FailingImplementationRuntime:\n    def __init__(self, *, mutation_applied: bool = False):\n        self.mutation_applied = mutation_applied\n\n    def execute(self, **_kwargs):\n        raise ImplementationRuntimeError(\n            "sanitized protected implementation failure",\n            mutation_applied=self.mutation_applied,\n        )\n\n\ndef test_pre_mutation_implementation_failure_is_durable_failed_run(tmp_path):\n    session, service, conversations, work_specs = service_for(tmp_path, "implementation-failure.db")\n    try:\n        run = activated_run(service, conversations, work_specs)\n        plan = AutonomyCoordinator(service, FakeExecutor()).run(\n            run_id=run.id, operation_key="plan-before-implement-failure", expected_revision=run.revision\n        )\n        assert plan.run.state == "IMPLEMENT"\n\n        result = AutonomyCoordinator(\n            service,\n            FakeExecutor(),\n            implementation_runtime=FailingImplementationRuntime(),\n        ).run(\n            run_id=run.id,\n            operation_key="implement-failure",\n            expected_revision=plan.run.revision,\n        )\n\n        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "FAILED"\n        assert result.run.resume_stage == "IMPLEMENT"\n        assert result.run.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"\n        attempts = [item for item in result.run.attempts if item.stage == "IMPLEMENT"]\n        assert len(attempts) == 1\n        assert attempts[0].status == "FAILED"\n        assert attempts[0].failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"\n        evidence = json.loads(attempts[0].evidence_json)\n        assert evidence == {"error_class": "ImplementationRuntimeError", "mutation_applied": False}\n        assert result.steps[-1].attempt_id == attempts[0].id\n    finally:\n        session.close()\n\n\ndef test_post_mutation_implementation_failure_stays_fail_closed_without_fabricated_attempt(tmp_path):\n    session, service, conversations, work_specs = service_for(tmp_path, "implementation-post-mutation.db")\n    try:\n        run = activated_run(service, conversations, work_specs)\n        plan = AutonomyCoordinator(service, FakeExecutor()).run(\n            run_id=run.id, operation_key="plan-before-post-mutation", expected_revision=run.revision\n        )\n        result = AutonomyCoordinator(\n            service,\n            FakeExecutor(),\n            implementation_runtime=FailingImplementationRuntime(mutation_applied=True),\n        ).run(\n            run_id=run.id,\n            operation_key="post-mutation-failure",\n            expected_revision=plan.run.revision,\n        )\n        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "IMPLEMENT"\n        assert [item for item in result.run.attempts if item.stage == "IMPLEMENT"] == []\n        assert result.steps[-1].outcome == "FAILED_AFTER_MUTATION"\n    finally:\n        session.close()\n''')

# 9. Protected implementation source-payload regression.
Path("services/api/tests/test_implementation_generation_context.py").write_text('''from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot\nfrom parallax_api.intelligence.implementation_generation import (\n    AcceptanceRequirement,\n    ImplementationGenerationRequest,\n    SOURCE_CONTEXT_AUTHORITY_RULE,\n)\n\n\ndef test_server_provided_source_satisfies_file_provision_precondition_without_relaxing_contract():\n    source = SourceContextSnapshot(\n        files=(SourceContextFile("apps/client/src/App.tsx", "a" * 64, 12, "export {};\\n"),),\n        digest="b" * 64,\n        total_bytes=12,\n        excluded_secret_files=0,\n        omitted_bounded_files=0,\n    )\n    request = ImplementationGenerationRequest(\n        work_specification_id="spec-1",\n        work_specification_revision=1,\n        work_specification_digest="c" * 64,\n        title="Animate logo",\n        objective="Animate the Parallax logo.",\n        constraints=(\n            "Repository files must be provided before implementation can proceed.",\n            "Preserve the existing visual language.",\n        ),\n        acceptance=(AcceptanceRequirement("AC-01", "The logo animates."),),\n        source_context=source,\n    )\n\n    source_payload = request.source_prompt_payload()\n    assert source_payload["runtime_source_access"] == "SERVER_PROVIDED_PROTECTED_SOURCE"\n    assert source_payload["runtime_source_authority_rule"] == SOURCE_CONTEXT_AUTHORITY_RULE\n    assert "must be provided" in request.contract_payload()["constraints"][0]\n    assert "substantive Work Specification constraints" in SOURCE_CONTEXT_AUTHORITY_RULE\n''')

# 10. Browser regression: after PLAN autonomy reaches IMPLEMENT, IMPLEMENT must
# still expose the autonomous continuation action rather than becoming a dead end.
replace(
    "apps/client/scripts/code-binding-smoke.mjs",
    '''      json(response, 200, {\n        run: engineeringRun,\n        stop_reason: 'EXECUTOR_UNAVAILABLE',\n        steps: [{ stage: 'EXECUTOR', outcome: 'FAILED', attempt_id: null, replayed: false, tool_id: 'python' }],\n      }, origin);\n''',
    '''      engineeringRun = {\n        ...engineeringRun,\n        state: 'IMPLEMENT',\n        revision: engineeringRun.revision + 1,\n        updated_at: new Date().toISOString(),\n        attempts: [...engineeringRun.attempts, {\n          id: '66666666-6666-4666-8666-666666666666',\n          stage: 'PLAN',\n          attempt_number: 1,\n          status: 'PASSED',\n          failure_code: null,\n          evidence: { executor_preflight: 'passed' },\n          started_at: new Date().toISOString(),\n          completed_at: new Date().toISOString(),\n        }],\n      };\n      json(response, 200, {\n        run: engineeringRun,\n        stop_reason: 'IMPLEMENTATION_REQUIRED',\n        steps: [{ stage: 'PLAN', outcome: 'PASSED', attempt_id: '66666666-6666-4666-8666-666666666666', replayed: false, tool_id: null }],\n      }, origin);\n''',
)
replace(
    "apps/client/scripts/code-binding-smoke.mjs",
    '''  await autonomy.click();\n  await page.getByText(/isolated executor unavailable; no plan state was changed/).waitFor({ timeout: 5000 });\n  await page.getByText('Code run · PLAN').waitFor({ timeout: 5000 });\n''',
    '''  await autonomy.click();\n  await page.getByText('Code run · IMPLEMENT').waitFor({ timeout: 5000 });\n  await page.getByText(/protected implementation can continue here/).waitFor({ timeout: 5000 });\n  await page.getByLabel('Run autonomously').waitFor({ timeout: 5000 });\n''',
)
replace(
    "apps/client/scripts/code-binding-smoke.mjs",
    '''  await reduced.getByText('Code run · PLAN').waitFor({ timeout: 5000 });\n''',
    '''  await reduced.getByText('Code run · IMPLEMENT').waitFor({ timeout: 5000 });\n''',
)
replace(
    "apps/client/scripts/code-binding-smoke.mjs",
    '''    boundedAutonomyStopState: true,\n''',
    '''    boundedAutonomyImplementContinuation: true,\n''',
)

print("Autonomous IMPLEMENT recovery edits applied")
