from pathlib import Path

path = Path('services/api/parallax_api/code/autonomy.py')
text = path.read_text(encoding='utf-8')
old = '''from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\nfrom .run_events import RunEventError\n'''
new = '''from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\nfrom .protected import STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE\nfrom .run_events import RunEventError\n'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '''                if stage is WorkflowStage.BUILD:\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                else:\n                    evidence["acceptance_ids_verified"] = acceptance_ids\n\n                passed = evidence.get("protected_success") is True\n'''
new = '''                if stage is WorkflowStage.BUILD:\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                elif (\n                    self.service.acceptance_verification_scope_for_run(run)\n                    == STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE\n                ):\n                    evidence["acceptance_verification_scope"] = STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                    evidence["acceptance_ids_verified"] = []\n                    evidence["acceptance_ids_unverified"] = acceptance_ids\n                else:\n                    evidence["acceptance_ids_verified"] = acceptance_ids\n\n                passed = evidence.get("protected_success") is True\n'''
assert text.count(old) == 1
path.write_text(text.replace(old, new, 1), encoding='utf-8')

path = Path('services/api/parallax_api/code/live_observability.py')
text = path.read_text(encoding='utf-8')
old = '''        "acceptance_ids_targeted",\n        "acceptance_ids_verified",\n    }\n)\n'''
new = '''        "acceptance_ids_targeted",\n        "acceptance_ids_verified",\n        "acceptance_ids_unverified",\n        "acceptance_verification_scope",\n    }\n)\n'''
assert text.count(old) == 1
path.write_text(text.replace(old, new, 1), encoding='utf-8')
