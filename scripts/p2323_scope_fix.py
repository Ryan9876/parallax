from pathlib import Path

p = Path('services/api/parallax_api/code/agentic_candidate_recovery.py')
t = p.read_text()
old = '''        rejections: list[CandidateRejection] = []\n        validator_rejected_agent_digests: list[str] = []\n        validator_repair_count = 0\n\n        try:\n'''
new = '''        rejections: list[CandidateRejection] = []\n\n        try:\n'''
assert old in t
t = t.replace(old, new, 1)
old = '''                    attempted_agents: list[str] = []\n                    rejection_count = 0\n                    previous_failure_kind: str | None = None\n\n                    while True:\n'''
new = '''                    attempted_agents: list[str] = []\n                    rejection_count = 0\n                    validator_rejected_agent_digests: list[str] = []\n                    validator_repair_count = 0\n                    previous_failure_kind: str | None = None\n\n                    while True:\n'''
assert old in t
t = t.replace(old, new, 1)
p.write_text(t)

# Add a source-level regression guard because the retry budget is required to be per work unit.
tp = Path('services/api/tests/test_agentic_candidate_recovery.py')
test = tp.read_text()
name = 'test_validator_repair_tracking_is_scoped_inside_each_scheduled_work_unit'
assert name not in test
test += f'''\n\ndef {name}():\n    import inspect\n    from parallax_api.code.agentic_candidate_recovery import ResilientLiveAgenticControlPlane\n\n    source = inspect.getsource(ResilientLiveAgenticControlPlane._proposal_for_plan)\n    unit_scope = source.index("for scheduled_assignment in ready:")\n    rejected_scope = source.index("validator_rejected_agent_digests: list[str] = []")\n    repair_scope = source.index("validator_repair_count = 0")\n    loop_scope = source.index("while True:")\n    assert unit_scope < rejected_scope < loop_scope\n    assert unit_scope < repair_scope < loop_scope\n''' 
tp.write_text(test)
print('scoped validator repair state per work unit')
