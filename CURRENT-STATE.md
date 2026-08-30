# Parallax 2.0 Current State

Date: 2026-08-30

Status: **WAVES 1–8 DEPLOYMENT-VERIFIED / PYTHON AND .NET SOURCE-ONLY FULL EXPERIENCE ACCEPTED / P2-V0.23.9 VALIDATOR-GUIDED CANDIDATE REPAIR DEPLOYMENT-VERIFIED + NORMAL-PATH PRODUCTION-ACCEPTED / P2-V0.23.10 HOSTED MODEL ESCALATION DEPLOYMENT-VERIFIED + PRODUCTION-ACCEPTED / P2-V0.23.8 BOUNDED CANDIDATE RECOVERY DEPLOYMENT-VERIFIED / W9-S1 P2-V0.23.7 GREENFIELD AUTHORITY IMPLEMENTED + API DEPLOYMENT-VERIFIED / CANONICAL GREENFIELD ACCEPTANCE PENDING FRESH APPROVED EMPTY TARGET / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION DEPLOYMENT-VERIFIED + PRODUCTION-ACCEPTED / RESUMED COMPONENT HEALTH CLIENT CORRECTION DEPLOYMENT-VERIFIED / LONG-RUNNING CLIENT RELEASE FRESHNESS DEPLOYMENT-VERIFIED**

## Current production truth

Parallax production now has verified end-to-end source-only engineering paths for both the established Python validation profile and the admitted .NET validation profile. In each accepted path, the bounded QA identity creates or reuses a Project, creates a conversation, produces and approves a Work Specification, activates an Engineering Run, bootstraps exact public GitHub source, advances through protected PLAN, IMPLEMENT, BUILD, TEST and VERIFY, stops at REVIEW, and returns an authenticated ZIP of the accepted source lineage.

W8-S2 is now complete. The former OT Time failure was reduced from public-source bootstrap, to missing .NET sandbox readiness, and finally to independent defects in the OT Time benchmark repository itself. Parallax now selects a dedicated server-owned .NET execution snapshot for `dotnet-v1`; production preflight verifies exact snapshot identity, deny-all networking, fixed toolchain readiness and source-free state. After the OT Time benchmark was independently repaired and validated, the canonical authenticated production replay reached REVIEW at revision 6 with no failure and verified the exact-lineage source-only handoff.

The public-source bootstrap remains independent from Vercel application delivery. Public commit-bearing GitHub source uses Git smart HTTP plus exact commit-addressed codeload archives. Source-only Projects do not require a Vercel Project, Preview target, application deployment, GitHub publication, or production-promotion authority.

P2-V0.23.8 / Architecture v3.22 is now production-deployment-verified. Rejected pre-mutation implementation candidates are distinct from worker/process loss and may recover only through deterministic, already-admitted alternate agents within the existing reassignment bound. Protected proposal validation and all canonical source, lineage, Git, deployment, and REVIEW authority remain unchanged.

P2-V0.23.9 / Architecture v3.23 is now production-deployment-verified and has a successful authenticated normal-path production replay. The production incident showed that all already-admitted alternates could independently return provider-successful proposals that the protected safe-patch validator rejected; later admitted candidates now receive only fixed server-owned validator-repair guidance after a bounded `VALIDATION_EXHAUSTED` classification. Provider/rate-limit failures remain separate, retry bounds are unchanged, and no mutation authority is added. The corrected post-deploy OT Time replay reached REVIEW at revision 6 with no failure and verified the authenticated source-only ZIP handoff. The replay did not artificially induce candidate rejection; branch-specific validator-guided recovery is established by deterministic protected tests.

The production client now projects resumed component health against the latest persisted control boundary rather than treating an older worker failure as current health forever. Historical failure events remain visible and unchanged. After a later persisted `RUN_CONTROL / RESUMED` event, an older dedicated worker failure is presented as `Awaiting evidence` until fresh worker evidence arrives. Worker IDs and source-lineage references on unrelated failed events are observation references only; they no longer cause Worker runtime or Source lineage to inherit that event failure. Dedicated lineage acceptance evidence remains authoritative for lineage health.

Safe deletion is now production-accepted. The previously deployed P2-V0.18.12 logical-deletion correction has an authenticated post-cutover production smoke proving the active-work 409 guard, terminal cancellation path, Project and bound-conversation disappearance from active reads, active slug/repository identity reuse, fixture cleanup, and zero external-provider mutation. Internal protected-evidence retention and non-owner authorization remain established by the exact-head regression suite; production does not expose a deleted-history audit read merely for QA.

W9-S1 empty-greenfield initialization authority is now implemented and production-deployment-verified under P2-V0.23.7 / Architecture v3.21. Parallax can positively inspect an exact credentialed repository as empty, create an explicit zero-file greenfield root lineage, preserve the ordinary protected lifecycle, and at REVIEW use a separate fixed `repository.initialize-empty` capability before ordinary bounded publication. The canonical Decision Ledger end-to-end acceptance is not yet complete because its fixed disposable repository was initialized by earlier Parallax QA fixture activity before this release; v3.21 did not mutate that target.

## P2-V0.23.10 — Hosted model escalation ordering — DEPLOYMENT-VERIFIED / PRODUCTION-ACCEPTED

Workstream: #453. Governing specification: `P2-V0.23.10`. Architecture: `ARCHITECTURE.md` v3.24.

Production evidence showed autonomous IMPLEMENT could invoke `openai/gpt-5.6-sol -> openai/gpt-5.6-terra -> openai/gpt-5.6-luna` even though the canonical hosted escalation policy is `Luna -> Terra -> Sol`. The cause was deterministic SHA-256 identity sorting inside agent-team orchestration, which unintentionally made an integrity identifier a routing priority.

The released implementation adds bounded server-owned selection priority to admitted-agent evidence and canonicalizes roster, selected-team and unit-eligibility order from that policy. Hosted implementation priorities are Luna `0`, Terra `1`, Sol `2`; equal priorities retain identity-digest tie determinism. Candidate-rejection recovery and the existing validator-guided repair path consume the same canonical admitted sequence. Capability admission, proposal validation, candidate validation, source mutation, lineage, Git/deployment and REVIEW authority are unchanged.

Release and production acceptance evidence:

- release PR: #467;
- exact green PR head: `50fa74cb9f8b14fe318e8c98bf86ed8bebb38627`;
- application release merge / deployed API source: `3077d719273b295b5ab9c05ea937cd5dae7fa76e`;
- production API deployment: `dpl_AMkcDM2iXkXEKqjraY7o4mKfZBPd`;
- deployment state: `READY` with canonical alias `parallax-api-tan.vercel.app` and no alias error;
- production `/health`: HTTP 200 / service `ok`; production `/ready`: HTTP 200 with database and providers `ok`;
- exact-head Workstream Spec Validation workflow `33293777463`: SUCCESS;
- exact-head Bounded Autonomy Pilot workflow `33293777452`: SUCCESS;
- exact-head Parallax P2 CI workflow `33293777468`: SUCCESS;
- authentic DSPy compile and protected `--require-dspy` validation plus focused orchestration/candidate-recovery/runtime-activation regression: PASS;
- one-shot dispatcher workflow `33294036729`: SUCCESS and dispatched only the existing trusted QA production replay;
- trusted QA Production Replay workflow `33294039327`: Python full experience job `99210536817` SUCCESS and OT Time replay job `99210536961` SUCCESS;
- representative OT Time Engineering Run `0e32e3af-040f-446f-81c6-fdad9ed27687` advanced from PLAN revision 1 through EXECUTOR, PLAN, IMPLEMENT, BUILD, TEST and VERIFY to REVIEW revision 6 with `last_failure_code=null` and `REVIEW_REQUIRED`;
- authenticated source-only handoff verified 32 ZIP entries / 74,820 bytes;
- exact production runtime logs for that autonomous request show `parallax_model_transport transport=vercel_ai_gateway model=openai/gpt-5.6-luna` and a successful Luna completion;
- exact deployment/time-window searches found no `openai/gpt-5.6-terra` or `openai/gpt-5.6-sol` invocation, proving the successful normal path began and ended on Luna without unnecessary escalation.

This production replay validates the intended first-choice routing path. It does not manufacture a rejected candidate to exercise Terra/Sol fallback; bounded alternate escalation remains established by protected deterministic regression tests. No production failure injector or validator relaxation was introduced for acceptance.

## Production components

### Client

Current deployment-verified client remains:

- application source: `8ad310ec0efeb54dbe6067d80878e40b91f8560d`;
- production deployment: `dpl_7CC8atxBusUuBXYnVg3XBzagSJ4E`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. Agent-runnable GitHub Actions OIDC maps to that same bounded QA principal without storing or exposing the QA password.

### API

Current deployment-verified production API:

- source: `3077d719273b295b5ab9c05ea937cd5dae7fa76e`;
- production deployment: `dpl_AMkcDM2iXkXEKqjraY7o4mKfZBPd`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- architecture: `ARCHITECTURE.md` v3.24.

The production build preflight restored and qualified both execution substrates before release:

- common Python/Node snapshot: `snap_vagbatADKKndxwFGSDNbt08Ueigm`;
- dedicated .NET snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- common snapshot: exact identity, deny-all networking, required Python dependencies, `node --version`, and source-free root verified;
- .NET snapshot: exact identity, deny-all networking, `dotnet --info` on .NET SDK 8.0.424, and source-free root verified.

Later main commits used only for authoritative-record and QA-harness reconciliation are not newer deployed API runtimes and must not be recorded as such. The current API runtime source remains the exact application source above.

## Long-running client release freshness — DEPLOYMENT-VERIFIED

A production observation exposed a second, distinct client issue after the resumed-component health correction was deployed: an iPhone Safari tab that had been opened before the new client release continued executing its already-loaded JavaScript while receiving later API events. The server and production alias were current, but the long-running tab had no mechanism to learn that a newer client shell existed. This can leave truthful fresh run events rendered through obsolete client projection logic until the operator manually reloads.

PR #463 adds an advisory web release guard without changing API or Engineering Run semantics. The loaded client records the same-origin hashed script/stylesheet signature from its shell, checks a no-cache `/index.html` release shell every 60 seconds and when the page regains focus, returns from the page cache, or becomes visible, and compares the current release signature. If a newer shell is present, Parallax shows an accessible persistent `Parallax was updated` notice with a minimum-44pt `Refresh now` action. It does not force-reload an active operator session. Network failures in the release check are non-disruptive. `/index.html` is explicitly served with `Cache-Control: public, max-age=0, must-revalidate` so the comparison cannot silently rely on an obsolete shell.

The same release closes the browser-level acceptance gap that allowed the original observation to escape automation. A 390×844 Playwright regression now reproduces the exact Activity sequence `#11 WORKER_STATE FAILED / AGENTIC_CANDIDATE_EXHAUSTED` → `#12 IMPLEMENT FAILED / AUTONOMOUS_IMPLEMENT_FAILED` → `#13 RUN_CONTROL RESUMED` → `#14 IMPLEMENT FAILED / AUTONOMOUS_IMPLEMENT_FAILED` on the actual operator Activity surface. The regression requires Component Health to preserve the historical failures in the timeline while projecting Worker runtime as `Awaiting evidence`, preserving accepted Source lineage as observed, and rejecting stale current `Attention` inherited from pre-resume worker evidence. A separate browser regression simulates a newer deployed shell while the old tab remains open and proves stale-client detection, explicit refresh availability, minimum mobile target sizing, and successful loading of the current shell after refresh.

Release evidence:

- release PR: #463;
- exact green PR head: `e77bdf22c3070a57638fdc4f3d15e733a932792e`;
- application release merge / deployed client source: `8ad310ec0efeb54dbe6067d80878e40b91f8560d`;
- production client deployment: `dpl_7CC8atxBusUuBXYnVg3XBzagSJ4E`;
- deployment state: `READY`;
- user-observed production alias `parallax-ashy-one-20.vercel.app` is attached to that deployment;
- Bounded Autonomy workflow `33292775470`: SUCCESS;
- Parallax P2 CI workflow `33292775471`: SUCCESS;
- Fast API/contracts, Fast client/typecheck/state/export/browser/Skia, protected promotion and DSPy release compilation: PASS;
- production release-check shell on `parallax-ashy-one-20.vercel.app`: HTTP 200 with `Cache-Control: public, max-age=0, must-revalidate`;
- exact deployment build error scan: clean.

A browser tab loaded before this release cannot retroactively contain the release guard and requires one final manual refresh. Once this release is loaded, later client deployments are detected by the guard on the bounded interval or page-return signals above. No API, persistence, persisted event, Engineering Run state machine, source-lineage authority, provider authority, deployment ceiling or REVIEW boundary changed.

## Client resumed-component health projection — DEPLOYMENT-VERIFIED

Production observation showed a truthful event history but a stale current-health projection: persisted event #11 recorded a failed Worker state (`AGENTIC_CANDIDATE_EXHAUSTED`), event #12 recorded failed IMPLEMENT (`AUTONOMOUS_IMPLEMENT_FAILED`), and later event #13 recorded `RUN_CONTROL / RESUMED`, while the authoritative Engineering Run was active in IMPLEMENT. The Component Health card nevertheless continued to show Worker runtime and Source lineage as current `Attention` from #11.

The defect was client-only. `componentHealth()` treated any event carrying `worker_execution_id` or `source_lineage_ref` as direct health evidence for those components and had no resume supersession rule. That allowed an unrelated failure to contaminate component health and allowed a historical worker failure to remain current after a persisted resume.

Correction and release evidence:

- release PR: #461;
- merged/deployed client source: `77cf1f4537023849f43c5b9eaaff9363ef77196c`;
- production client deployment: `dpl_7rLxgFh9CH3aY9sdoSCTnD1xHDV3`;
- deployment state: `READY`;
- production alias observed by the user: `parallax-ashy-one-20.vercel.app`;
- Bounded Autonomy workflow `33291202942`: SUCCESS;
- Parallax P2 CI workflow `33291202984`: SUCCESS;
- Fast API/contracts, Fast client/typecheck/state/export/browser/Skia, protected promotion and DSPy release compilation: PASS.

Current-health projection now separates dedicated component evidence from reference-only evidence. A newer persisted resume boundary supersedes an older dedicated worker failure for current-health presentation, yielding `Awaiting evidence` until fresh component evidence exists; it does not erase or rewrite the historical failure event. Source lineage uses dedicated lineage/acceptance evidence when available, while a lineage reference on another subsystem's failed event is observation-only. Worker execution references receive the same observation-only treatment. GitHub and Vercel remain `Unavailable` until their own persisted evidence exists.

This release changes no API, persisted event, Engineering Run state-machine, source-lineage authority, provider authority, deployment ceiling or REVIEW boundary.

## P2-V0.23.9 — Validator-guided alternate-candidate repair — DEPLOYMENT-VERIFIED / NORMAL-PATH PRODUCTION-ACCEPTED

Workstream: #456 (completed).

Governing specification: `P2-V0.23.9`.

Architecture: `ARCHITECTURE.md` v3.23.

Production incident evidence:

- affected Engineering Run: `2b3cd15f-c5e2-481a-8266-c92c6534b08b`;
- all three already-admitted hosted implementation candidates completed provider calls but were rejected by the unchanged protected proposal validator;
- terminal evidence: `AGENTIC_CANDIDATE_EXHAUSTED` / `AUTONOMOUS_IMPLEMENT_FAILED`;
- canonical source mutation: none;
- defect: alternate-candidate recovery was finite and safe but blind to the bounded fact that a prior candidate had failed strict safe-patch validation.

P2-V0.23.9 preserves the validator and every mutation/authority ceiling. Only a server-classified `VALIDATION_EXHAUSTED` result may cause a later already-admitted candidate for the same work unit to receive fixed server-owned safe-patch repair guidance. The guidance restates exact path/digest binding and strict single-file unified-diff form only. Provider/rate-limit failures remain separate. The existing eligible-agent roster and `max_reassignments_per_work_unit` bound remain authoritative, and no new same-model or unbounded retry loop exists.

Release evidence:

- release PR: #457;
- exact green release head: `682faae2eadfeb63698a8fffc0ee772cba89348d`;
- application release merge / deployed source: `f0706d489b26ff715891f75c8d2723fb0f734c3b`;
- production API deployment: `dpl_Dz9dNegGMSdY1GoZdzD2tThQbATm`;
- deployment state: `READY`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database and providers ready;
- provider/storage, exact-repository delivery-token, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, execution-snapshot and run-event preflights: PASS;
- exact deployment error/fatal runtime-log scan: clean;
- workstream contract and protected-plan validation, Bounded Autonomy/full API regression, client/browser/Skia, protected promotion and DSPy release compilation: PASS.

Post-deploy acceptance was intentionally non-destructive and did not manufacture a validator failure. The first trusted replay `33289874294` already proved the released runtime could progress through PLAN, IMPLEMENT, BUILD, TEST and VERIFY to REVIEW revision 6 with no runtime failure; that job failed only after REVIEW because the QA harness called the obsolete `/v1/engineering-runs/{run}/source-archive` route and received HTTP 404. Harness-only PR #459 corrected verification to the existing Project-scoped authenticated `/source-download` endpoint and merged as `a4d7cc83f2e3c60619e19d735c63af843742647e`; no application runtime changed.

Corrected trusted workflow-dispatch acceptance:

- workflow run: `33290221272`;
- W8 OT Time job: `99200534358` — SUCCESS;
- Project: `7b4c2377-6f06-4b43-b174-206e059e24f0`;
- Engineering Run: `cb9a75aa-413b-4f6c-b019-e493fa112655`;
- initial state/revision: PLAN / 1;
- final stop/state/revision: `REVIEW_REQUIRED` / REVIEW / 6;
- `last_failure_code`: null;
- PLAN, IMPLEMENT, BUILD, TEST and VERIFY: PASSED;
- IMPLEMENT tool: `safe-source-implementation-v1`;
- authenticated source-only ZIP handoff: 32 entries / 74,870 bytes;
- companion Python full-experience job `99200534320`: SUCCESS.

The corrected production replay succeeded on its first admitted `openai/gpt-5.6-sol` implementation candidate, so validator-guided alternate-candidate repair was not artificially triggered in production. That branch is established by deterministic protected regression tests covering bounded failure classification, validation-only next-candidate guidance, provider-failure separation, finite recovery, bounded diagnostics and unchanged authority. Production acceptance therefore combines exact-source deployment verification, clean normal-path full-experience replay, and deterministic protected proof of the repair branch rather than weakening or deliberately tripping the production validator.

## P2-V0.23.8 — Bounded rejected-candidate recovery — DEPLOYMENT-VERIFIED

Workstream: #446.

Governing specification: `P2-V0.23.8`.

Production incident evidence:

- affected Engineering Run: `0cb9e8c5-1381-4913-a890-7bd48bc0384f`;
- prior runtime: `dpl_8LBreMU3LGxUR8RWW8LfSCJRGxxx`;
- hosted `openai/gpt-5.6-sol` call completed successfully, then the server-owned proposal validator emitted `parallax_model_route validation_failed`;
- the rejected proposal did not mutate canonical source;
- pre-v3.22 behavior incorrectly projected that candidate rejection as `AGENTIC_TASK_FAILED` and persisted `AUTONOMOUS_IMPLEMENT_FAILED`.

Architecture v3.22 now separates pre-mutation candidate rejection from worker/process loss. A rejected proposal remains non-authoritative and non-mutating. The same work unit may retry only through another already-admitted eligible implementation agent in deterministic server-owned order, with incremented assignment generation and fresh dispatch identity. Recovery is capped by the existing `max_reassignments_per_work_unit` bound. Exhaustion fails closed as bounded `CANDIDATE_GENERATION_EXHAUSTED` evidence with `worker_process_loss=false`; protected proposal validation, safe mutation, lineage, Git, deployment and REVIEW authority are unchanged.

Release evidence:

- release PR: #447;
- exact green release head: `22e96f20378c1e91e1c105a0e62c4865a7034510`;
- application release merge: `319f548b5950ba1c27603ccf0c5921d5a3aaee5f`;
- production deployment: `dpl_H6oQUkxyzX9C32VEHgWiRwLpZr1G`;
- deployment state: `READY`;
- exact deployment source: `319f548b5950ba1c27603ccf0c5921d5a3aaee5f`;
- production provider/storage, exact-repository scoped delivery permission, projected-source, private Blob, lineage-composition, agentic-runtime, projected-bootstrap, run-event schema and execution-snapshot preflights: PASS;
- exact-head full API regression, Bounded Autonomy, client state/type/export, browser/Skia, changed-spec protected DSPy plan, DSPy release compilation and protected-promotion gates: PASS;
- authentic P2-V0.23.8 DSPy qualification used `ollama_chat/qwen2.5-coder:1.5b` and passed `--require-dspy` before merge.

Post-deploy regression used the existing bounded QA OIDC identity against `github:Ryan9876/Movies`: workflow run `33285758959`, rerun job `99191707001` — **SUCCESS**. Engineering Run `f13e9c12-b0ca-47ac-a0ba-b5578f2e5c62` reached `REVIEW` revision `6`, `last_failure_code=null`, stop reason `REVIEW_REQUIRED`; EXECUTOR, PLAN, IMPLEMENT, BUILD, TEST and VERIFY all passed; authenticated source archive verification passed with 7 entries / 1404 bytes; `source_publication=false`; `app_deployment=false`.

That post-deploy run proves normal production execution remains healthy but its first implementation candidate was accepted. It therefore does **not** claim that the candidate-rejection retry branch happened naturally in production. The retry/exhaustion branch is established by deterministic protected regression tests and the exact-head release gates; no production failure injector or weakened validator was introduced merely to manufacture that observation.

## P2-V0.23.6 — Profile-qualified protected execution snapshots — DEPLOYMENT-VERIFIED

Workstream: #438.

Governing specification: `P2-V0.23.6`.

Durable contract:

- deterministic validation-profile selection remains source-derived and separate from execution-snapshot selection;
- `python-v1` and the reserved `node-v1` identity retain the established common snapshot;
- `dotnet-v1` requires the dedicated `PARALLAX_EXECUTION_SNAPSHOT_DOTNET_ID` snapshot and never falls back to the common image;
- snapshot mapping is finite and server-owned; unrecognized profiles and missing/malformed dedicated configuration fail closed;
- candidate and canonical same-lineage validation use the same selected snapshot identity;
- fixed validation commands and the existing bounded PREPARE authority are unchanged;
- no user Engineering Run installs an SDK/toolchain dynamically;
- production preflight verifies every enabled snapshot before the deployment can become qualified;
- the snapshot contains toolchain state only, never Project/application source or credentials.

Release evidence:

- architecture: `ARCHITECTURE.md` v3.20;
- application release merge: `e204d69ed0d6a9a69d68374ad63e8a1dbd630813`;
- production deployment: `dpl_8e87ZdYGACUvf4YvivsSWwomDE5n`;
- deployment state: `READY`;
- dedicated .NET snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- canonical OT Time production acceptance: workflow `33280783143`, attempt 2 — PASS.

Vercel remains an isolated execution/infrastructure provider for this substrate; it is not an application-delivery dependency for `source-only` Projects.

## W8-S2 .NET source-only full experience — ACCEPTED

Acceptance target: `github:Ryan9876/ot-time`.

Authorized canonical QA workflow: `.github/workflows/w8-s2-qa-replay.yml`.

Final workflow run: `33280783143`, attempt `2`.

Final workflow job: `99177057782` / `replay-public-ot-time-source-only` — **SUCCESS**.

Exact production evidence:

- Project: `7b4c2377-6f06-4b43-b174-206e059e24f0`;
- Engineering Run: `82170d38-24ff-4f91-af2a-e247ebbe17a7`;
- initial state/revision: `PLAN` / `1`;
- final state/revision: `REVIEW` / `6`;
- `last_failure_code`: `null`;
- public source bootstrap: PASS;
- deterministic validation profile: `dotnet-v1`;
- dedicated qualified snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- PLAN through VERIFY protected advancement: PASS;
- authenticated source ZIP integrity check: PASS;
- ZIP contained the accepted source lineage and generated `PARALLAX_QA.md` (`135` bytes);
- application deployment: not required;
- Vercel Preview target: not required;
- source publication: not required.

The workflow concluded: `Public OT Time source-only run reached REVIEW: revision=6; failure=none` and `Authenticated source-only handoff verified; no Vercel target or Preview was required.`

### Benchmark prerequisite repaired independently

The first post-release replay correctly selected and restored the new .NET snapshot and passed `dotnet --info`, but `dotnet restore` failed. An unrestricted .NET 8.0.424 diagnostic proved the failure reproduced outside Parallax. The OT Time repository had invalid/inconsistent package references, a vulnerable MailKit version treated as an error, overlapping one-commit scaffold implementations, and test-harness analyzer defects.

OT Time PR #2 repaired that benchmark without weakening its behavioral assertions. Exact validated OT Time head `b0174da80adea4f30d724214923de623734a2c4a` passed:

- `dotnet restore OtTime.sln --nologo` — PASS;
- `dotnet build OtTime.sln --no-restore --nologo` — PASS with 0 warnings / 0 errors;
- `dotnet test OtTime.sln --no-restore --nologo` — PASS, 9/9 tests.

OT Time PR #2 merged as `2a369b9d79967ca603172d33c1bb941d1630b2a9`. This target-repository repair is not a Parallax application deployment and did not widen Parallax runtime authority.

## Production Python source-only full experience — ACCEPTED

Acceptance target: `github:Ryan9876/Movies`.

Authorized QA workflow: `.github/workflows/qa-production-replay.yml`.

Final canonical workflow run: `33277189927`.

Final canonical workflow job: `99165862378` / `python-full-experience` — **SUCCESS**.

Exact production evidence:

- Project: `d00e23cb-6d84-4805-bf15-4f738d920136`;
- Engineering Run: `e9a1772f-88b3-450c-b619-8008de8c9576`;
- final state: `REVIEW`;
- final revision: `6`;
- `last_failure_code`: `null`;
- stop reason: `REVIEW_REQUIRED`;
- executor: `python` — PASSED;
- PLAN — PASSED;
- IMPLEMENT — PASSED using `safe-source-implementation-v1`;
- BUILD — PASSED;
- TEST — PASSED;
- VERIFY — PASSED;
- source ZIP: verified;
- required generated acceptance file: `PARALLAX_QA_PYTHON.md` present;
- source publication: `false`;
- application deployment: `false`.

The companion Python regression in QA Production Replay `33287875970`, job `99194169048`, also passed while the safe-deletion production acceptance was executed. This confirms the accepted common-snapshot Python source-only path remained healthy during the deletion verification.

## Safe deletion — DEPLOYMENT-VERIFIED / PRODUCTION-ACCEPTED

Workstream: #290.

Corrective specification: `P2-V0.18.12`.

Corrective release evidence:

- initial logical-deletion merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- production migration: `20260827173141` / `safe_conversation_project_deletion` — applied;
- corrective PR: #294;
- corrective merge: `109444dcd7e13bfe842dea71355607941258b073`;
- production API deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- deployment state: `READY`;
- exact corrective deployment source: `109444dcd7e13bfe842dea71355607941258b073`;
- post-cutover `/health` and `/ready`: HTTP 200;
- exact corrective API deployment error/fatal scan: clean;
- unauthenticated protected conversation route: HTTP 401;
- exact-head specification, API, Bounded Autonomy, client, protected lifecycle and deletion regressions: PASS.

Final authenticated production behavior was accepted through the existing trusted `QA Production Replay` OIDC identity:

- workflow run: `33287875970`;
- job: `99194168944` / `safe-deletion-production-smoke` — **SUCCESS**;
- disposable Project: `4e062e22-e706-4dbb-ac14-e1319d2b82ff`;
- disposable conversation: `2c990ee7-61bc-4499-b0f9-8c467a61b472`;
- Work Specification: `5d3e7000-b252-4bdf-8395-ad2a84d347e8`;
- protected Engineering Run: `0851a300-0041-4d46-a7a6-8d03a1609af1`;
- run activation: `PLAN` revision `1`;
- Project delete while protected work was active: HTTP `409`, with the Project remaining active;
- protected run cancellation: `CANCELLED` revision `2`;
- Project delete after terminal cancellation: HTTP `204`;
- deleted Project active read: HTTP `404`;
- deleted bound-conversation active read: HTTP `404`;
- active-list checks: deleted Project and conversation absent;
- exact slug/repository active identity reuse: HTTP `201`, new Project `c37ae153-e653-49d1-9d11-76125a7e38f1`;
- replacement Project cleanup: HTTP `204`, followed by `404` active read;
- synthetic repository identity: `github:Ryan9876/qa-safe-delete-33287875970-1`;
- external provider mutation authorized: `false`;
- external provider resource created: `false`;
- external provider resource deleted: `false`;
- bounded evidence artifact: `safe-deletion-production-evidence-33287875970-1`, artifact `9725006991`, 602 bytes, ZIP SHA-256 `719d17a92d69d8c1050b6fd9d84f9110ead17d8c2eb34845448432fa346e65ae`.

The production smoke establishes the server-authoritative user-visible destructive behavior without deleting a real GitHub repository, Vercel deployment, or other provider resource. Production active-owner routes intentionally hide logically deleted Project-bound records, so this smoke does not manufacture a deleted-history audit endpoint to prove physical retention. Protected Work Specifications, Engineering Runs, attempts, events, source-lineage evidence, immutable artifacts, cross-owner failure behavior, historical-unbound owner requirements and active-row uniqueness remain established by the exact-head regression suite that qualified the deployed P2-V0.18.12 semantics.

A first standalone smoke workflow correctly failed OIDC session exchange with HTTP 401 before creating any fixture because the bounded QA trust policy did not authorize that workflow identity. The acceptance run was moved into the already-authorized `QA Production Replay` workflow rather than widening authentication. The one-shot destructive job was removed after successful evidence capture; `scripts/qa_safe_deletion_smoke.sh` remains as a bounded reusable harness.

## Public source bootstrap — DEPLOYMENT-VERIFIED

Architecture v3.20 incorporates the v3.19 public-source authority boundary unchanged.

For a public GitHub repository with a commit-bearing default branch, production:

1. resolves canonical HEAD/default-branch identity through unauthenticated Git smart HTTP;
2. pins the immutable commit;
3. reads source from the exact commit-addressed GitHub codeload archive;
4. applies bounded archive, path, file-type, size and UTF-8 validation;
5. exposes read-only repository/source capability only;
6. never silently constructs a Vercel-backed credential path merely because the public transport is throttled or unavailable.

Private/non-public source remains fail-closed behind exact repository authority. Empty greenfield repositories remain a separate initialization/mutation-authority problem because there is no existing commit to read.

## Wave 8 — COMPLETE / PRODUCTION-ACCEPTED

W8-S1, W8-S3 and W8-S4 remain deployment-verified. W8-S2 is now also production-accepted.

Wave 8 now has both general source-backed experience evidence and the previously missing .NET protected-validation evidence. The canonical OT Time replay proves the former missing-static-target/source-bootstrap/toolchain sequence no longer reproduces and that the durable run remains within the REVIEW/source-only authority ceiling.

Workstreams #377 and #438 may be closed as completed on the exact evidence above.

## Wave 9 S1 — Real-world greenfield benchmark

Control Tower: #391.

Workstream: #392.

Governing benchmark specification: `P2-V0.23.0`.

Benchmark-admission release:

- qualified worker head: `1d053823d08d8e5050e77c624dafcd09199fe942`;
- application release merge: `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- production API deployment: `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

Greenfield repository-authority remediation:

- finding: #406;
- governing remediation specification: `P2-V0.23.3`;
- qualified implementation head: `1cad61de06ce4d1da4aaec12f4f4da97d16b63a3`;
- application release merge: `0cfe499ac787a23142067e95e80af80dedab36c5`;
- production deployment: `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

The frozen Decision Ledger benchmark remains open. Its original empty-repository observation is a valid failed reference observation rather than a passing application benchmark. P2-V0.23.7 now supplies the previously missing governed empty-greenfield authority; however, the former disposable target was consumed by legacy Parallax QA fixture activity before v3.21. A fresh approved truly empty target is therefore required to complete the canonical end-to-end trial without rewriting repository history.

## P2-V0.23.7 — Empty-greenfield repository authority — DEPLOYMENT-VERIFIED / CANONICAL TARGET REPLACEMENT REQUIRED

Workstream follow-up: #442.

Architecture: `ARCHITECTURE.md` v3.21.

Release evidence:

- release PR: #443;
- exact green release head: `a36a81d379e8f9b696f0879afa7126c31761a0e8`;
- application release merge: `2619aada4d3fd732589c6489a99ebe95dcc0d01d`;
- production API deployment: `dpl_8LBreMU3LGxUR8RWW8LfSCJRGxxx`;
- deployment state: `READY`;
- exact deployment source: `2619aada4d3fd732589c6489a99ebe95dcc0d01d`;
- production provider/storage preflight: PASS;
- exact-repository scoped delivery-token preflight: PASS;
- projected-source, private Blob, lineage composition and agentic-runtime preflights: PASS;
- exact-head specification, API regression, Bounded Autonomy, client/browser/Skia, DSPy release compilation and protected-promotion gates: PASS.

Durable behavior now supports a positively authenticated empty GitHub repository without manufacturing source or widening authority. Empty classification requires exact credentialed inspection; ambiguous/provider failures remain fail-closed. A zero-file `greenfield` root is explicit durable lineage, and accepted implementation must become non-empty before validation. Missing repository authorization is surfaced as structured `REPOSITORY_AUTHORIZATION_REQUIRED` with same-run retry. Empty-baseline mutation is REVIEW-only, fixed, idempotent and isolated behind `repository.initialize-empty`; normal GitHub delivery, Preview ceiling and human REVIEW boundary remain unchanged.

### Canonical Decision Ledger acceptance target was consumed before v3.21

The fixed target `Ryan9876/sickbeard` is no longer an empty repository. Its root commit `b7e8399724e38ee60b3380aa02ecb079a43acee3` was created at `2026-08-29T20:46:01Z` with message `Initialize minimal Parallax QA source fixture`, followed by four serial commits titled `Complete minimal Parallax QA source fixture`. Those commits predate the v3.21 production deployment by roughly nineteen minutes and contain QA-only fixture content. They are therefore not evidence that the v3.21 greenfield initializer ran.

After v3.21 became READY, bounded QA replay `33285377567` / job `99187551677` obtained the existing approved `parallax://qa-production` OIDC identity, but `scripts/w9_s1_reference_trial.sh` correctly stopped at its preflight with `Decision Ledger target is no longer greenfield; refusing to start trial.` No new Project/run or v3.21 repository mutation was created by that attempt.

The repository history is preserved rather than destructively rewritten. Canonical AC-27 remains pending a fresh user-approved truly empty repository with exact GitHub App/Vercel Connect coverage and the required Preview target readiness. This is an acceptance-fixture prerequisite, not an unverified runtime implementation claim.

## Wave 9 S2 — Governed skill intake and capability catalog

Control Tower: #391.

Workstream: #395.

Governing specification: `P2-V0.23.1`.

Release:

- qualified worker head: `0965969da3224ebe62e8a33348440b5753e76d6e`;
- application release merge: `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production API deployment: `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

S2 remains non-executing capability intake. External observations are quarantined metadata until exact approval and existing registry admission succeed; discovered content receives no package-install, generic shell/network, provider, merge, deployment, or REVIEW authority.

## Other open governed work

- #442 — P2-V0.23.7 empty-greenfield authority is implementation- and deployment-verified; canonical Decision Ledger acceptance remains pending a fresh approved empty target because the prior disposable target was consumed by legacy QA fixture activity.

## Authoritative-record update

`CURRENT-STATE.md` was updated again after deployment verification of the resumed-component-health client correction. It records the production symptom, client-only projection root cause, exact merged source and READY deployment, successful release gates, and the rule that historical failures remain intact while current health follows later persisted resume/component evidence.

`ARCHITECTURE.md` remains authoritative at v3.23 because this correction changes no durable lifecycle, authority, persistence, recovery or provider contract; it fixes only how existing persisted evidence is projected in the client.

`DESIGN-SYSTEM.md` was not changed because no durable visual token, component pattern or interaction rule changed.

`PROJECT-CONSTITUTION.md` was not changed because no constitutional product or authority principle changed.

`CURRENT-STATE.md` was updated after P2-V0.23.9 exact-source deployment verification and successful authenticated normal-path production acceptance. It records the original validator-exhaustion incident, the bounded repair semantics, release/deployment evidence, the obsolete-QA-route finding and correction, the corrected REVIEW/source-handoff replay, and closure of #456. #442 remains the only listed open governed work.

`ARCHITECTURE.md` was advanced to v3.23 because P2-V0.23.9 introduces a durable candidate-recovery rule: only bounded server-classified validation rejection may project fixed safe-patch repair guidance to a later already-admitted candidate, while provider failures, retry bounds, mutation authority and lifecycle ceilings remain unchanged.

`DESIGN-SYSTEM.md` was not changed because this release does not alter durable visual or interaction-system rules.

`PROJECT-CONSTITUTION.md` was not changed because the release preserves existing least-privilege, explicit-authority, fail-closed validation and evidence-preservation principles rather than introducing a new constitutional rule.
