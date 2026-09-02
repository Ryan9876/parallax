from pathlib import Path

path = Path('services/api/parallax_api/code/autonomy.py')
text = path.read_text(encoding='utf-8')
old = '''from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\nfrom .run_events import RunEventError\n'''
new = '''from .implementation_runtime import ImplementationRuntimeError, ProtectedImplementationRuntime\nfrom .protected import STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE\nfrom .run_events import RunEventError\n'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '''from .validation_toolchains import (\n    ExecutionContract,\n    ExecutionContractIdentity,\n    ValidationProfileError,\n    ValidationProfileReason,\n)\n'''
new = '''from .validation_toolchains import (\n    ExecutionBindingReason,\n    ExecutionContract,\n    ExecutionContractCode,\n    ExecutionContractIdentity,\n    ValidationProfileError,\n    ValidationProfileReason,\n)\n'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '''                stage_key = self._stage_key(operation_key, stage, run.revision)\n                spec = self.registry.spec_for(stage, operation_key=stage_key)\n                try:\n                    accepted_lineage = self._accepted_implementation_lineage(run)\n'''
new = '''                stage_key = self._stage_key(operation_key, stage, run.revision)\n                spec = self.registry.spec_for(stage, operation_key=stage_key)\n                execution_contract: ExecutionContract | None = None\n                try:\n                    accepted_lineage = self._accepted_implementation_lineage(run)\n'''
assert text.count(old) == 1
text = text.replace(old, new, 1)
old = '''                acceptance_ids = sorted(item["id"] for item in self.service.acceptance_map_for_run(run))\n                if stage is WorkflowStage.BUILD:\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                else:\n                    evidence["acceptance_ids_verified"] = acceptance_ids\n\n                passed = evidence.get("protected_success") is True\n'''
new = '''                acceptance_ids = sorted(item["id"] for item in self.service.acceptance_map_for_run(run))\n                if stage is WorkflowStage.BUILD:\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                elif (\n                    execution_contract is not None\n                    and execution_contract.contract_id is ExecutionContractCode.STATIC_WEB\n                    and execution_contract.binding_reason is ExecutionBindingReason.GREENFIELD_STATIC_WEB\n                ):\n                    evidence["acceptance_verification_scope"] = STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE\n                    evidence["acceptance_ids_targeted"] = acceptance_ids\n                    evidence["acceptance_ids_verified"] = []\n                    evidence["acceptance_ids_unverified"] = acceptance_ids\n                else:\n                    evidence["acceptance_ids_verified"] = acceptance_ids\n\n                passed = evidence.get("protected_success") is True\n'''
assert text.count(old) == 1
path.write_text(text.replace(old, new, 1), encoding='utf-8')

path = Path('services/api/parallax_api/code/live_observability.py')
text = path.read_text(encoding='utf-8')
old = '''        "acceptance_ids_targeted",\n        "acceptance_ids_verified",\n    }\n)\n'''
new = '''        "acceptance_ids_targeted",\n        "acceptance_ids_verified",\n        "acceptance_ids_unverified",\n        "acceptance_verification_scope",\n    }\n)\n'''
assert text.count(old) == 1
path.write_text(text.replace(old, new, 1), encoding='utf-8')
