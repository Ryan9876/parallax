from pathlib import Path

repo_path = Path('services/api/parallax_api/repositories/worker_executions.py')
text = repo_path.read_text()
old_import = '''from ..code.worker_recovery import (
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerStaleLease,
)'''
new_import = '''from ..code.worker_recovery import (
    RecoveryAction,
    WorkerLeaseConflict,
    WorkerLeaseExpired,
    WorkerLifecycleState,
    WorkerStaleLease,
)'''
if old_import not in text:
    raise SystemExit('worker repository import anchor not found')
text = text.replace(old_import, new_import, 1)

reassign_anchor = '    def reassign(self, *, run_id: str, now: datetime, lease_seconds: int) -> EngineeringWorkerExecution:\n'
prepare_method = '''    def prepare_human_resume(
        self,
        *,
        run_id: str,
        now: datetime,
    ) -> EngineeringWorkerExecution | None:
        current = self.get_for_run(run_id)
        if current is None:
            return None
        if current.state != WorkerLifecycleState.FAILED.value:
            return current
        if current.lease_owner_id is not None or current.lease_expires_at is not None:
            raise WorkerLeaseConflict("FAILED worker execution must be unleased before human resume recovery")

        result = self.session.execute(
            _cas(
                update(EngineeringWorkerExecution)
                .where(
                    EngineeringWorkerExecution.id == current.id,
                    EngineeringWorkerExecution.revision == current.revision,
                    EngineeringWorkerExecution.state == WorkerLifecycleState.FAILED.value,
                    EngineeringWorkerExecution.lease_owner_id.is_(None),
                    EngineeringWorkerExecution.lease_expires_at.is_(None),
                )
                .values(
                    state=WorkerLifecycleState.RECOVERING.value,
                    retry_count=0,
                    no_progress_count=0,
                    oscillation_count=0,
                    progress_fingerprint=None,
                    previous_progress_fingerprint=None,
                    stall_classification=None,
                    blocker_code=None,
                    next_recovery_action=RecoveryAction.REASSIGN.value,
                    revision=current.revision + 1,
                    updated_at=now,
                )
            )
        )
        if result.rowcount != 1:
            self.session.rollback()
            raise WorkerLeaseConflict("human-resume worker recovery lost a concurrent compare-and-swap race")
        self.session.commit()
        refreshed = self.get(current.id)
        if refreshed is None:
            raise RuntimeError("worker execution disappeared after human-resume recovery preparation")
        return refreshed

'''
if reassign_anchor not in text:
    raise SystemExit('worker repository reassign anchor not found')
text = text.replace(reassign_anchor, prepare_method + reassign_anchor, 1)
repo_path.write_text(text)

service_path = Path('services/api/parallax_api/code/worker_service.py')
text = service_path.read_text()
begin_anchor = '    def begin_recovery(self, *, run_id: str, now: datetime | None = None) -> EngineeringWorkerExecution:\n'
service_method = '''    def prepare_human_resume(
        self,
        *,
        run_id: str,
        now: datetime | None = None,
    ) -> EngineeringWorkerExecution | None:
        self._run(run_id)
        current = self.executions.get_for_run(run_id)
        if current is None or current.state != WorkerLifecycleState.FAILED.value:
            return current
        execution = self.executions.prepare_human_resume(run_id=run_id, now=_utc(now))
        if execution is None:
            return None
        self._emit_worker_event(
            execution,
            event_key=f"worker:{execution.id}:state:{execution.revision}:HUMAN_RESUME_RECOVERING",
            outcome=RunEventOutcome.RECOVERING,
            summary="Explicit Engineering Run resume re-armed the terminal worker for one new bounded generation.",
        )
        return execution

'''
if begin_anchor not in text:
    raise SystemExit('worker service begin recovery anchor not found')
text = text.replace(begin_anchor, service_method + begin_anchor, 1)
service_path.write_text(text)

route_path = Path('services/api/parallax_api/routes/engineering_runs.py')
text = route_path.read_text()
old_resume = '''@router.post("/{run_id}/resume", response_model=EngineeringOperationRead)
def resume(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "resume", svc)
'''
new_resume = '''@router.post("/{run_id}/resume", response_model=EngineeringOperationRead)
def resume(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    prior = invoke(lambda: svc.get(run_id))
    result = invoke(lambda: svc.resume(run_id=run_id, **payload.model_dump()))
    if prior.state == "FAILED" and result.run.state != "FAILED":
        invoke(lambda: worker_recovery_service(svc).prepare_human_resume(run_id=run_id))
    return result_payload(result, svc)
'''
if old_resume not in text:
    raise SystemExit('engineering run resume route anchor not found')
text = text.replace(old_resume, new_resume, 1)
route_path.write_text(text)

test_path = Path('services/api/tests/test_worker_recovery.py')
text = test_path.read_text()
if 'def test_explicit_human_resume_rearms_terminal_worker_for_one_new_generation' in text:
    raise SystemExit('human resume tests already present')
text += r'''


def test_explicit_human_resume_rearms_terminal_worker_for_one_new_generation(tmp_path):
    Session = db_context(tmp_path, "human-resume-worker.db")
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session, max_retries=0, max_no_progress=99, max_oscillations=99)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0)
        failed = service.checkpoint(
            lease,
            checkpoint(
                binding,
                step="IMPLEMENT",
                lineage=LINEAGE_A,
                lkg=LINEAGE_A,
                evidence_refs=("validation:terminal-candidate-exhaustion",),
            ),
            authoritative_source_lineage_ref=LINEAGE_A,
            retry=True,
            now=T0 + timedelta(seconds=1),
        ).execution
        assert failed.state == WorkerLifecycleState.FAILED.value
        assert failed.lease_owner_id is None
        assert failed.retry_count == 1
        assert failed.checkpoint_revision == 1
        assert failed.source_lineage_ref == LINEAGE_A
        assert failed.last_known_good_lineage_ref == LINEAGE_A
        checkpoint_json = failed.checkpoint_json
        checkpoint_revision = failed.checkpoint_revision
        current_step = failed.current_step
        generation = failed.lease_generation
        worker_id = failed.id
        failure_revision = failed.revision

        with pytest.raises(WorkerLeaseConflict, match="protected recovery or is final"):
            service.acquire(run_id=binding.run_id, now=T0 + timedelta(seconds=2))

        prepared = service.prepare_human_resume(run_id=binding.run_id, now=T0 + timedelta(seconds=3))
        assert prepared is not None
        assert prepared.id == worker_id
        assert prepared.state == WorkerLifecycleState.RECOVERING.value
        assert prepared.lease_owner_id is None
        assert prepared.lease_expires_at is None
        assert prepared.lease_generation == generation
        assert prepared.checkpoint_json == checkpoint_json
        assert prepared.checkpoint_revision == checkpoint_revision
        assert prepared.current_step == current_step
        assert prepared.source_lineage_ref == LINEAGE_A
        assert prepared.last_known_good_lineage_ref == LINEAGE_A
        assert prepared.retry_count == 0
        assert prepared.no_progress_count == 0
        assert prepared.oscillation_count == 0
        assert prepared.progress_fingerprint is None
        assert prepared.previous_progress_fingerprint is None
        assert prepared.stall_classification is None
        assert prepared.blocker_code is None
        assert prepared.next_recovery_action == RecoveryAction.REASSIGN.value
        assert prepared.revision == failure_revision + 1

        replay = service.prepare_human_resume(run_id=binding.run_id, now=T0 + timedelta(seconds=4))
        assert replay is not None
        assert replay.id == worker_id
        assert replay.revision == prepared.revision
        assert replay.lease_generation == generation

        replacement = service.reassign(
            run_id=binding.run_id,
            now=T0 + timedelta(seconds=5),
            lease_seconds=30,
        )
        assert replacement.execution_id == worker_id
        assert replacement.generation == generation + 1
        current = service.executions.get_for_run(binding.run_id)
        assert current is not None
        assert current.state == WorkerLifecycleState.REASSIGNED.value
        assert current.retry_count == 0
        assert current.checkpoint_revision == checkpoint_revision
        assert current.source_lineage_ref == LINEAGE_A
    finally:
        session.close()


def test_human_resume_prepare_does_not_rearm_nonfailed_worker(tmp_path):
    Session = db_context(tmp_path, "human-resume-nonfailed.db")
    binding = insert_bound_run(Session)
    session, service = recovery_service(Session)
    try:
        lease = service.acquire(run_id=binding.run_id, now=T0)
        before = service.executions.get_for_run(binding.run_id)
        assert before is not None
        prepared = service.prepare_human_resume(run_id=binding.run_id, now=T0 + timedelta(seconds=1))
        assert prepared is not None
        assert prepared.state == WorkerLifecycleState.RUNNING.value
        assert prepared.revision == before.revision
        assert prepared.lease_generation == lease.generation
        assert prepared.lease_owner_id == lease.owner_id
    finally:
        session.close()
'''
test_path.write_text(text)
