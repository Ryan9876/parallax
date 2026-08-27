from pathlib import Path

runtime = Path("services/api/parallax_api/code/agentic_runtime_live.py")
text = runtime.read_text(encoding="utf-8")
stale = "request.source_context.content_digest"
count = text.count(stale)
if count != 2:
    raise SystemExit(f"expected exactly two stale source-context field reads, found {count}")
text = text.replace(stale, "request.source_context.digest")
runtime.write_text(text, encoding="utf-8")

tests = Path("services/api/tests/test_agentic_runtime_activation.py")
body = tests.read_text(encoding="utf-8")
marker = "def test_live_agent_task_binds_real_source_context_digest_before_dispatch"
if marker in body:
    raise SystemExit("regression test already exists")
body += r'''


class _DispatchCheckpointReached(RuntimeError):
    pass


class _DispatchCheckpointProbe:
    def __init__(self):
        self.steps: list[tuple[str, str, tuple[str, ...]]] = []
        self.stopped = False

    def acquire(self, *, run_id: str):
        return WorkerLease(
            execution_id="dispatch-probe",
            run_id=run_id,
            owner_id="worker:dispatch-probe",
            generation=1,
            expires_at=datetime.now(timezone.utc),
        )

    def checkpoint(
        self,
        lease,
        *,
        plan,
        work_unit_id: str,
        source_lineage_ref: str,
        step: str,
        evidence_refs: tuple[str, ...],
        state=WorkerLifecycleState.CHECKPOINTED,
    ):
        self.steps.append((step, source_lineage_ref, evidence_refs))
        if step == "AGENT_DISPATCH":
            raise _DispatchCheckpointReached("dispatch checkpoint reached")
        return lease

    def stop_bounded(self, *, run_id: str) -> None:
        self.stopped = True


def test_live_agent_task_binds_real_source_context_digest_before_dispatch(tmp_path):
    from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
    from parallax_api.intelligence.implementation_generation import (
        AcceptanceRequirement,
        ImplementationGenerationRequest,
    )

    session, service, _, run, allocator, _, base = create_runtime_fixture(
        tmp_path,
        "live-source-context-digest",
        [
            "Create the one approved proof file.",
            "Preserve all existing source bytes.",
        ],
    )
    try:
        control = live_control(service, allocator)
        coordinator = AutonomyCoordinator(
            service,
            LegacyExecutor(),
            plan_runtime=control,
        )
        planned = coordinator.run(
            run_id=run.id,
            operation_key="w6-r1:source-context-plan",
            expected_revision=run.revision,
        )
        assert planned.run.state == WorkflowStage.IMPLEMENT.value

        current = service.get(run.id)
        plan = control._verify_plan_evidence(
            run=current,
            base_source_lineage_ref=base.lineage_id,
            source_content_digest=base.content_digest,
        )
        context_digest = sha256(b"bounded-live-source-context").hexdigest()
        source = SourceContextSnapshot(
            files=(
                SourceContextFile(
                    path="app.py",
                    sha256=sha256(b"value = 1\n").hexdigest(),
                    size=len(b"value = 1\n"),
                    content="value = 1\n",
                ),
            ),
            digest=context_digest,
            total_bytes=len(b"value = 1\n"),
            excluded_secret_files=0,
            omitted_bounded_files=0,
        )
        acceptance = tuple(
            AcceptanceRequirement(id=str(item["id"]), text=str(item["text"]))
            for item in service.acceptance_map_for_run(current)
        )
        request = ImplementationGenerationRequest(
            work_specification_id=current.work_specification_id or "",
            work_specification_revision=int(current.work_specification_revision or 0),
            work_specification_digest=current.work_specification_digest or "",
            title="Bound live source-context identity",
            objective="Reach the durable S1 dispatch checkpoint without changing authority.",
            constraints=("Preserve exact source authority.",),
            acceptance=acceptance,
            source_context=source,
        )

        probe = _DispatchCheckpointProbe()
        control.worker_bridge = probe
        with pytest.raises(_DispatchCheckpointReached):
            control._proposal_for_plan(
                plan,
                request,
                proposal_validator=lambda proposal: True,
                alternative_round=1,
            )

        assert probe.stopped is True
        assert len(probe.steps) == 1
        step, lineage_ref, evidence_refs = probe.steps[0]
        assert step == "AGENT_DISPATCH"
        assert lineage_ref == base.lineage_id
        assert any(item.startswith("task:") for item in evidence_refs)
        assert context_digest != base.content_digest
    finally:
        session.close()
'''
tests.write_text(body, encoding="utf-8")
