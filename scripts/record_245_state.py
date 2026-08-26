from pathlib import Path

path = Path('CURRENT-STATE.md')
text = path.read_text(encoding='utf-8')

old_header = '''Release: Wave 5 generalized application delivery remains the production platform baseline, with production stabilization hotfix #246 **deployment-verified on top of Wave 5**. Hotfix candidate `7eaa290fd57a2a333976ed882f29075f9d022e3f` merged to `main` as `36548611c3806d08d6fbfcdb686fe2a025956194`; production API deployment `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB` is READY on that exact merge SHA. The hotfix contains no client-runtime change, so deployment-verified client `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn` remains current production. Operator functional retest of the original fresh-Code-objective flow is still pending.
Date: 2026-08-25
Status: **WAVE 5 RELEASED / HOTFIX #246 DEPLOYMENT-VERIFIED / API READY / OPERATOR FUNCTIONAL RETEST PENDING / CLIENT RETAINED AND VERIFIED / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**
'''
new_header = '''Release: Wave 5 generalized application delivery remains the production platform baseline, with production stabilization hotfixes #244, #245 and #246 **deployment-verified on top of Wave 5**. The current application release is `main@464aa9f106348638cfd436aa427398edbd3e1583`; production API deployment `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and production client deployment `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm` are READY on that exact merge SHA. Hotfix #246 has also passed the operator functional retest against the `OT Time` Project.
Date: 2026-08-26
Status: **WAVE 5 RELEASED / PRODUCTION STABILIZATION #244-#246 DEPLOYMENT-VERIFIED / API READY / CLIENT READY / #246 FUNCTIONAL RETEST PASSED / DURABLE FAILURE OBSERVABILITY VERIFIED / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**
'''
assert old_header in text
text = text.replace(old_header, new_header, 1)

marker = '## Production stabilization hotfix #246 — deployment-verified / operator retest pending\n'
assert marker in text
section = '''## Production stabilization hotfix #245 — deployment-verified

Production acceptance testing exposed a truthful-state gap after a pre-mutation protected IMPLEMENT failure. Engineering Run `95944752-1e5a-45e2-a7ce-ebc56e36413c` was durably `FAILED` with `resume_stage=IMPLEMENT` and `last_failure_code=AUTONOMOUS_IMPLEMENT_FAILED`, but its optional run-event projection stopped at PLAN. The cause was a projection-contract mismatch: authoritative failed-attempt evidence already contained sanitized `mutation_applied=false`, while the run-event metadata allowlist rejected that field after the Engineering Run/attempt transaction had committed. The `/autonomous` request therefore surfaced a generic HTTP 422 and Live Build showed sparse component evidence rather than the known durable failure.

Issue #245 / PR #251 corrected the reporting boundary without changing execution authority:

- `mutation_applied` is now an allowlisted bounded run-event metadata field, so future durably failed IMPLEMENT attempts project a matching append-only `STAGE_RESULT / IMPLEMENT / FAILED` event with sanitized failure code and error class;
- if an optional run-event projection fails after the exact expected pre-mutation failure has already committed, autonomy verifies the durable attempt/run identity and returns the structured `IMPLEMENTATION_FAILED` result instead of replacing it with the projection exception;
- Live Build now treats authoritative `FAILED` plus `resume_stage`/`last_failure_code` as the truth fallback, explicitly rendering `IMPLEMENT failed` / `AUTONOMOUS_IMPLEMENT_FAILED` even when worker, source-lineage, GitHub, Vercel or evaluation evidence is unavailable;
- no historical event is fabricated or backfilled, and absent worker/source/provider/preview/evaluation success remains absent.

Exact candidate `7aebfb65d46df57ed38031d3e213a27dc9fe6303` passed Bounded Autonomy #564 (`32924005835`) and P2 CI #926 (`32924005964`), including full API regression, client typecheck/state/export, browser/Skia acceptance with a sparse-event FAILED/IMPLEMENT fixture, protected Code/Engineering/Reason promotion and regression rejection, and release DSPy compilation/verification. Both Vercel candidate checks succeeded before expected-head PR #251 merged to `main` as `464aa9f106348638cfd436aa427398edbd3e1583`.

Production deployment verification established:

- API deployment `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` is `READY`, target `production`, exact Git SHA `464aa9f106348638cfd436aa427398edbd3e1583`, with `aliasError=null` and canonical API aliases including `parallax-api-tan.vercel.app`;
- the API build passed registered-provider/source-tree/private-Blob, exact repository delivery-permission, projected-source, immutable Blob, lineage composition/rollback, projected bootstrap/runtime/process-recreation/replay/no-stage-mutation/project-rollback, execution-snapshot/deny-all/offline-dependency/no-repository-source and run-event schema preflights;
- `/health` and `/ready` both returned HTTP 200, with database/provider readiness intact and one registered provider target;
- deployment-scoped API `error`/`fatal` runtime logs returned no entries after cutover;
- client deployment `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm` is `READY`, target `production`, exact Git SHA `464aa9f106348638cfd436aa427398edbd3e1583`, `aliasError=null`, owns `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app` and `parallax-git-main-lew7.vercel.app`, and the production root returned HTTP 200.

The immediate rollback references are API deployment `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81` from hotfix #244 and client deployment `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn` from the pre-#245 production client. Hotfix #245 changes no constitutional authority, Project/repository authority, review/deployment authority, schema or credential/configuration surface.

## Production stabilization hotfix #244 — deployment-verified

Issue #244 / PR #250 moved repository-identity conflict detection to the correct authority boundary after testing proved that a Work Specification could target `Ryan9876/ot-time` while the selected Project was canonically bound to `github:ryan9876/parallax`. The implementation runtime had already failed closed before mutation; the hotfix additionally blocks Work Specification approval and re-checks Engineering Run activation when an explicit requested repository target conflicts with the selected Project. It never auto-switches or mutates Projects, and contextual/dependency repository references remain non-authoritative.

Exact candidate `40f8bc25fcfad6c725e795ade96dcb2f8c28d88` passed Workstream Spec Validation #357 (`32922601423`), Bounded Autonomy #563 (`32922601392`) and P2 CI #924 (`32922601357`) before PR #250 merged as `e818bc9f44e473195a1bfd7f82b3c0cb3abf7e42`. Production API deployment `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81` reached `READY` on that exact merge SHA with clean health/readiness/runtime-error evidence and all production build preflights passing. Hotfix #244 contained no client-runtime change. It is now the immediate API rollback reference behind #245.

'''
text = text.replace(marker, section + '## Production stabilization hotfix #246 — deployment-verified / functional retest passed\n', 1)

text = text.replace(
    '## Production stabilization hotfix #246 — deployment-verified / operator retest pending',
    '## Production stabilization hotfix #246 — deployment-verified / functional retest passed',
)
text = text.replace(
    'Issue #246 remains open until the operator repeats the original fresh `OT Time` Code-objective flow in production and confirms it reaches `SPEC · NOT CAPTURED` without `PROTECTED_SCOPE_FAILURE` before Work Specification capture.',
    'The production functional retest passed: under the same `OT Time` Project `9e898865-b98e-41d3-b000-bdc87bad377f` bound to `github:ryan9876/ot-time`, fresh Code conversation `085bb6e7-ba2a-4770-b08e-e25618350534` persisted the operator objective `Create an about page` exactly once and returned `Objective captured. Capture the Work Specification to continue with governed Code execution.` without `PROTECTED_SCOPE_FAILURE`. Issue #246 is therefore closed completed.',
)
text = text.replace(
    'Operator functional retest of the fresh-Code-objective regression remains pending.',
    'The fresh-Code-objective production functional retest passed and issue #246 is closed completed.',
)

old_api = '''The deployment-verified production API/runtime binary is Vercel deployment `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB` from stabilization hotfix merge `main@36548611c3806d08d6fbfcdb686fe2a025956194`, layered on the Wave 5 release. It is `READY`, has no alias error, and owns `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`. Live post-cutover health/readiness/authentication checks and deployment-scoped error/fatal scans are clean as recorded above. Operator functional retest of the fresh-Code-objective regression remains pending.

The deployment-verified production client remains Vercel deployment `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn` from application head `main@ff8e2395df081ebff376d703dfd97f3c10008240`. Wave 5 changes no client-runtime file, so its release-triggered client deployment was canceled/ignored as expected rather than replacing the binary. The retained client is `READY`, has no alias error, owns `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`, and served HTTP 200 after the Wave 5 API cutover.
'''
new_api = '''The deployment-verified production API/runtime binary is Vercel deployment `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` from stabilization release `main@464aa9f106348638cfd436aa427398edbd3e1583`, layered on the Wave 5 release. It is `READY`, has no alias error, owns `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`, and passed the full production preflight chain plus live health/readiness and deployment-scoped error/fatal verification recorded above.

The deployment-verified production client is Vercel deployment `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm` from the same stabilization release `main@464aa9f106348638cfd436aa427398edbd3e1583`. It is `READY`, has no alias error, owns `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`, and served HTTP 200 after cutover. This client adds the durable FAILED/resume-stage Live Build fallback introduced by hotfix #245 while preserving the existing visual language and protected execution/review boundaries.
'''
assert old_api in text
text = text.replace(old_api, new_api, 1)

old_rollbacks = '''The immediately preceding known-good API production deployment `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc` from Wave 5 release `main@c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains `READY` and is the immediate rollback reference for hotfix #246. Earlier known-good API references `dpl_ExFCK2iMVDbJbRiBZcL4faspHaw5` and `dpl_2L4R6g3em7LJc7XWdRp5rueGFRK1` remain available. Routine rollback remains non-destructive and follows the existing flag-first/application-deployment policy.

The client did not change in Wave 5. Its immediately preceding known-good fallback `dpl_vDHBaGyi4q3pAGvNpULJwi8p95RR` remains available as the client rollback candidate, while current production remains `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn`.

This `CURRENT-STATE.md` reconciliation is a record-only repository change and must not be treated as a new application/runtime binary release when merged. Current API runtime identity remains `main@36548611c3806d08d6fbfcdb686fe2a025956194` / `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB`; the Wave 5 base release remains `main@c39b5352be940f4052baa65c7cdd9d7c3ec773bb` / `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc`, and the retained client remains `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn`.
'''
new_rollbacks = '''The immediately preceding known-good API production deployment is hotfix #244 deployment `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81` from `main@e818bc9f44e473195a1bfd7f82b3c0cb3abf7e42`. The preceding hotfix #246 API `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB`, Wave 5 API `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc`, and earlier `dpl_ExFCK2iMVDbJbRiBZcL4faspHaw5` / `dpl_2L4R6g3em7LJwi8p95RR` references remain historical known-good evidence where applicable. Routine rollback remains non-destructive and follows the existing flag-first/application-deployment policy.

The immediately preceding known-good production client is `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn`; earlier client fallback `dpl_vDHBaGyi4q3pAGvNpULJwi8p95RR` also remains available. Current production client is `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm`.

This `CURRENT-STATE.md` reconciliation is a record-only repository change and must not be treated as a new application/runtime binary release when merged. Current application/runtime identity remains `main@464aa9f106348638cfd436aa427398edbd3e1583`, with API `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and client `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm`; the Wave 5 base release remains `main@c39b5352be940f4052baa65c7cdd9d7c3ec773bb` / API `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc`.
'''
assert old_rollbacks in text
text = text.replace(old_rollbacks, new_rollbacks, 1)

# Avoid leaving the old pending phrase anywhere in the current stabilization record.
text = text.replace('deployment-verified / operator retest pending', 'deployment-verified / functional retest passed')
path.write_text(text, encoding='utf-8')
