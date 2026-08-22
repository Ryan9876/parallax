# Parallax App-Builder Evaluation and Observability Spine — Workstream Specification

Status: APPROVED FOR IMPLEMENTATION
Spec ID: P2-V0.14.46
Workstream ID: WS-APP-EVAL-OBSERVABILITY
Tracking issue: #46
Base commit: 82e2a587e5974e908ca449e416f062919754cd9f
Method: Spec-first protected evaluation

> `P2-V0.14.46` is a validator-compatible workstream specification identity only. It is not a Parallax product release/version claim. The current protected spec validator accepts only `P2-Vx.y.z` identifiers; this workstream does not modify that shared validator.

## 1. Objective

Create a protected, provider-neutral app-builder evaluation and observability contract that can judge whether future increases in implementation and tool autonomy satisfy held-out success and safety requirements.

The first slice must evaluate recorded observable evidence rather than demos, model confidence, hidden reasoning, or provider-specific implementation details. It must make app-builder regressions deterministic to detect and difficult to hide behind aggregate scores.

## 2. Scope

This workstream owns an additive app-builder evaluation layer with:

- versioned `development` and `promotion` benchmark suites under `benchmarks/parallax-app-builder/`;
- typed immutable benchmark, recorded-evidence, case-result, category-result, and evaluation-report contracts;
- deterministic scoring with explicit machine-readable failure reasons;
- protected category and aggregate floors;
- recorded good fixtures for development and promotion suites;
- deliberate promotion regression fixtures that must fail;
- observable evidence hygiene checks for secrets and hidden-reasoning/scratchpad fields;
- an offline validation CLI that validates suites/evidence and returns a non-zero exit code on protected failure;
- integration notes that map future accepted Project, implementation, and tool-authority interfaces to this provider-neutral evidence contract.

Required protected behavior categories are:

1. `project_isolation` — project/workspace identity is explicit and cross-project leakage or mutation is denied;
2. `spec_binding` — implementation evidence is bound to the intended approved specification identity/revision/digest;
3. `implementation_evidence` — IMPLEMENT success requires bounded inspectable artifact/diff evidence rather than prose or a claimed demo;
4. `build_test_verify_truth` — BUILD/TEST/VERIFY success is represented only when the corresponding observable execution evidence succeeds;
5. `tool_authority` — denied or out-of-scope actions remain denied and model/user text cannot self-grant authority;
6. `interruption_recovery` — interruption/resume/idempotency behavior preserves project/run identity and does not duplicate or skip protected work;
7. `evidence_hygiene` — stored benchmark/evaluation evidence excludes secrets, credentials, hidden chain-of-thought, reasoning traces, and scratchpads.

The initial evaluator consumes provider-neutral observations and identifiers. It does not import unmerged #43, #44, or #45 implementation contracts.

## 3. Fixed decisions and interfaces

- Development and promotion suites are separate files with explicit purpose fields.
- Promotion expected contracts are not optimizer inputs.
- Deterministic protected evaluation remains structurally above optimization.
- A higher aggregate score cannot compensate for a critical safety failure.
- Recorded evidence contains observable identifiers, states, result codes, digests, and bounded facts only.
- Raw hidden reasoning is neither requested nor accepted as evidence.
- Secret-bearing payloads fail closed using the existing protected evaluation security scanner.
- The app-builder evaluator is additive and does not alter existing Engineering, Reason, or Code protected thresholds.
- The first slice does not modify `.github/workflows/**`, `protected_metrics.py`, or the existing generic evaluation schema/scorer/promotion modules.
- Future serialized integration may adapt field mappings to accepted #43/#44/#45 contracts without weakening this benchmark contract.

The provider-neutral case contract may require and forbid exact observable tokens. Examples include project binding, workspace binding, specification identity, patch/diff digest presence, successful/failed stage result identity, explicit authority denial, interruption recovery identity, and evidence-hygiene markers. Tokens are evidence vocabulary, not executable commands or provider credentials.

## 4. Non-goals

- Creating the durable Project/App model owned by #43.
- Implementing or applying source patches owned by #44.
- Defining the server-owned capability registry or provider adapters owned by #45.
- Changing current Code/Reason/Engineering protected thresholds.
- Wiring new promotion gates into CI in this first parallel slice.
- Granting Git commit, push, merge, Vercel promotion, database mutation, or production-deploy authority.
- Running provider-backed model evaluation as a prerequisite for offline correctness.
- Storing raw candidate chain-of-thought, scratchpads, hidden reasoning, credentials, or secret environment values.
- Treating benchmark success as merge or deployment authorization.

## 5. Architecture and failure semantics

The new evaluator lives in `services/api/parallax_api/evaluation/app_builder.py` but remains logically separate from optimizer-controlled code and existing protected promotion internals.

Benchmark files are data-only JSON. The evaluator loads and validates a suite, validates recorded evidence, checks evidence safety, scores each case deterministically, aggregates by protected category, and returns a typed report. The report contains digests and failures, not raw secret-bearing execution payloads.

The evaluator must fail closed when:

- suite/evidence identity or purpose does not match;
- duplicate or unknown case IDs are present;
- required categories/floors do not exactly match suite cases;
- a critical required observation is absent;
- a forbidden observation is present;
- a protected category or aggregate floor is missed;
- the payload contains secret material or forbidden hidden-reasoning fields;
- evidence claims a successful protected stage while the required observable success evidence is absent;
- a recorded authority-denial case instead shows an allowed/self-granted action.

Validation must be reproducible without network or provider credentials.

## 6. Security

- Treat all recorded app-builder evidence as untrusted input.
- Reuse the existing evaluation `security_findings` / `assert_safe_payload` boundary rather than creating a weaker competing scanner.
- Reject forbidden reasoning keys such as `chain_of_thought`, `hidden_reasoning`, `reasoning_trace`, and `scratchpad` anywhere in the payload.
- Reject configured secret values and likely credential literals.
- Never place credentials, provider tokens, raw secret environment values, arbitrary shell text, or private scratch reasoning in benchmark fixtures or evaluation reports.
- Evidence may include non-secret opaque project/run/spec identifiers and cryptographic digests.
- Failure reports expose machine-readable reason codes and bounded public metadata only.

## 7. Acceptance criteria

### AC-01 Spec-first authorization
This specification exists on the isolated workstream branch and passes `python scripts/validate_spec.py specs/P2-WS-APP-EVAL-OBSERVABILITY.md --spec-only` before substantive evaluator implementation is created.

### AC-02 Versioned suite separation
Separate versioned development and promotion suite files exist, declare their purpose explicitly, contain no duplicate case IDs, and each cover all seven required app-builder categories with exact protected category floors.

### AC-03 Typed observable contracts
The additive evaluator defines strict typed contracts for app-builder suites, cases, recorded evidence, case results, category results, and reports. Unknown fields and malformed identities fail validation rather than being silently accepted.

### AC-04 Deterministic protected scoring
Given the same suite and recorded evidence, evaluation produces the same case/category scores and machine-readable failure reasons. Critical failures block protected pass even when the aggregate numeric score would otherwise meet its floor.

### AC-05 Project/spec/implementation truthfulness
Protected cases verify project/workspace isolation, exact specification binding, and bounded implementation artifact/diff evidence. Cross-project evidence, mismatched specification binding, or prose-only IMPLEMENT claims are rejected.

### AC-06 Build/test/verify and authority truthfulness
Protected cases reject fabricated BUILD/TEST/VERIFY success and reject self-granted or out-of-scope tool authority. Provider/tool failure remains distinguishable from success.

### AC-07 Interruption and recovery
Protected cases require interruption/resume evidence to preserve project/run identity and idempotency semantics; fixtures that duplicate protected work, skip required state, or resume under the wrong identity fail.

### AC-08 Evidence hygiene
Automated tests prove secret-bearing payloads and forbidden hidden-reasoning/scratchpad fields are rejected. Stored evaluation reports contain digests, scores, result identities, and failure codes rather than raw secret or hidden-reasoning content.

### AC-09 Known-good and regression fixtures
Recorded good fixtures pass both development and promotion suites. At least one deliberate promotion regression fixture fails protected evaluation for multiple independent reasons, including at least one critical safety failure.

### AC-10 Offline CLI
`scripts/validate_app_builder_benchmark.py` validates/evaluates the additive benchmark without provider credentials or network model calls, writes or prints concise observable results, returns `0` for protected pass, and returns non-zero for malformed or protected-failing evidence.

### AC-11 Existing-boundary preservation
Focused tests prove this slice does not require changes to existing Engineering/Reason/Code protected thresholds, shared promotion rules, `.github/workflows/**`, Project persistence, patch application, or provider capability adapters.

### AC-12 Integration readiness
An integration note documents how accepted #43 Project identity, #44 implementation evidence, and #45 authority audit contracts can map into the provider-neutral observation vocabulary, and identifies future CI/promotion wiring as serialized Integration work rather than worker-owned release authority.

## 8. Risks and mitigations

- **Interface drift from #43/#44/#45:** keep the first slice provider-neutral and adapt mappings during serialized integration.
- **Benchmark gaming:** use separate held-out promotion cases, critical failures, exact category floors, and no optimizer access to promotion expected contracts.
- **False confidence from synthetic fixtures:** document that this is a protected contract baseline, not complete proof of app-builder quality; add real integration evidence later.
- **Accidental contract collision:** remain within the issue reservation and do not edit shared evaluator/CI/project/tool/patch paths without coordination.
- **Sensitive evidence leakage:** fail closed through existing security scanning and digest raw outputs where possible.

## 9. Release gate

This worker slice may be called **generated** when the approved spec and additive implementation/benchmark artifacts exist.

It may be called **validated** only when:

- the protected spec-only gate passes;
- focused app-builder evaluation tests pass;
- known-good development and promotion fixtures pass;
- deliberate regression fixtures are demonstrably rejected;
- security/hidden-reasoning negative tests pass;
- the offline CLI demonstrates both zero and non-zero exit paths; and
- the branch is ready for a PR with exact changed paths, evidence, risks, and integration notes.

This worker must not call the slice merged, deployed, or deployment-verified. Merge/deployment and future CI/promotion wiring remain Integration / Control Tower responsibilities.