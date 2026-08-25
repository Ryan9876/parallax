from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text()
    if old not in text:
        raise SystemExit(f"anchor missing in {path}")
    target.write_text(text.replace(old, new, 1))


replace(
    "services/api/tests/test_implementation_runtime.py",
    '''        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "IMPLEMENT"\n        assert result.steps[-1].stage == "IMPLEMENT"\n        assert result.steps[-1].outcome == "FAILED"\n        assert target.read_text(encoding="utf-8") == "value = 1\\n"\n''',
    '''        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "FAILED"\n        assert result.run.resume_stage == "IMPLEMENT"\n        assert result.run.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"\n        assert result.steps[-1].stage == "IMPLEMENT"\n        assert result.steps[-1].outcome == "FAILED"\n        failed = [item for item in result.run.attempts if item.stage == "IMPLEMENT"]\n        assert len(failed) == 1\n        assert failed[0].status == "FAILED"\n        assert failed[0].failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"\n        assert target.read_text(encoding="utf-8") == "value = 1\\n"\n''',
)

replace(
    "services/api/tests/test_runtime_credential_functional_proof.py",
    '''        # runtime. This proof intentionally supplies no implementation proposal,\n        # so the bounded run must cross PLAN into IMPLEMENT and then fail closed\n        # before mutation rather than stopping at the legacy implementation seam.\n        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "IMPLEMENT"\n        assert [step.stage for step in result.steps] == ["EXECUTOR", "PLAN", "IMPLEMENT"]\n        assert result.steps[-1].outcome == "FAILED"\n''',
    '''        # runtime. This proof intentionally supplies no implementation proposal,\n        # so the bounded run must cross PLAN into IMPLEMENT and then record an\n        # explicit pre-mutation failure rather than stopping at a silent active seam.\n        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED\n        assert result.run.state == "FAILED"\n        assert result.run.resume_stage == "IMPLEMENT"\n        assert result.run.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"\n        assert [step.stage for step in result.steps] == ["EXECUTOR", "PLAN", "IMPLEMENT"]\n        assert result.steps[-1].outcome == "FAILED"\n        failed = [item for item in result.run.attempts if item.stage == "IMPLEMENT"]\n        assert len(failed) == 1\n        assert failed[0].status == "FAILED"\n''',
)

print("Legacy IMPLEMENT failure tests aligned to durable FAILED semantics")
