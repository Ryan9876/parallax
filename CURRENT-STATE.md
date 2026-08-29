# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–8 DEPLOYMENT-VERIFIED / PYTHON AND .NET SOURCE-ONLY FULL EXPERIENCE ACCEPTED / W9-S1 CONTROLLED REFERENCE OBSERVATION COMPLETE WITH GREENFIELD INITIALIZATION AUTHORITY STILL OPEN / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production now has verified end-to-end source-only engineering paths for both the established Python validation profile and the admitted .NET validation profile. In each accepted path, the bounded QA identity creates or reuses a Project, creates a conversation, produces and approves a Work Specification, activates an Engineering Run, bootstraps exact public GitHub source, advances through protected PLAN, IMPLEMENT, BUILD, TEST and VERIFY, stops at REVIEW, and returns an authenticated ZIP of the accepted source lineage.

W8-S2 is now complete. The former OT Time failure was reduced from public-source bootstrap, to missing .NET sandbox readiness, and finally to independent defects in the OT Time benchmark repository itself. Parallax now selects a dedicated server-owned .NET execution snapshot for `dotnet-v1`; production preflight verifies exact snapshot identity, deny-all networking, fixed toolchain readiness and source-free state. After the OT Time benchmark was independently repaired and validated, the canonical authenticated production replay reached REVIEW at revision 6 with no failure and verified the exact-lineage source-only handoff.

The public-source bootstrap remains independent from Vercel application delivery. Public commit-bearing GitHub source uses Git smart HTTP plus exact commit-addressed codeload archives. Source-only Projects do not require a Vercel Project, Preview target, application deployment, GitHub publication, or production-promotion authority.

The separate W9-S1 empty-greenfield initialization boundary remains open. A repository with no public commit has no source revision for the public read-only transport to bootstrap, so canonical greenfield initialization still needs exact explicit repository mutation authority or another governed initialization mechanism.

## Production components

### Client

Current deployment-verified client remains:

- application source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- production deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. Agent-runnable GitHub Actions OIDC maps to that same bounded QA principal without storing or exposing the QA password.

### API

Current deployment-verified production API:

- source: `e204d69ed0d6a9a69d68374ad63e8a1dbd630813`;
- production deployment: `dpl_8e87ZdYGACUvf4YvivsSWwomDE5n`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`;
- architecture: `ARCHITECTURE.md` v3.20.

The production build preflight restored and qualified both execution substrates before release:

- common Python/Node snapshot: `snap_vagbatADKKndxwFGSDNbt08Ueigm`;
- dedicated .NET snapshot: `snap_qO26lCgjTq7xvQOpWctqy8xFyvZ1`;
- common snapshot: exact identity, deny-all networking, required Python dependencies, `node --version`, and source-free root verified;
- .NET snapshot: exact identity, deny-all networking, `dotnet --info` on .NET SDK 8.0.424, and source-free root verified.

Later `main` commit `fd96a8352b70799cb32db66bc83832b972a9ef36` is a QA-harness-only alignment of the canonical W8-S2 replay to P2-V0.23.6. It is not a newer deployed API runtime and must not be recorded as such.

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

Final workflow run: `33277189927`.

Final workflow job: `99165862378` / `python-full-experience` — **SUCCESS**.

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

This remains the clean production proof for the established common-snapshot Python path and guards against regression while .NET uses its dedicated snapshot.

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

The frozen Decision Ledger benchmark remains open. Its original empty-repository observation is a valid failed reference observation rather than a passing application benchmark. No target source was seeded out of band. Public-source bootstrap cannot manufacture an initial commit; explicit exact repository mutation authority or another governed greenfield initialization mechanism remains required before the canonical implementation trial can pass.

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

- #406 — code-side greenfield repository-authority remediation is deployment-verified; canonical empty-repository initialization authority remains unresolved for W9-S1;
- #290 — safe deletion final authenticated destructive smoke remains open.

## Authoritative-record update

`CURRENT-STATE.md` was updated after the deployment-verified P2-V0.23.6 release and successful authenticated W8-S2 OT Time production acceptance. It now records the exact runtime deployment, qualified snapshots, canonical workflow, Project, Engineering Run, lifecycle state/revision and source-only ZIP handoff evidence and marks Wave 8 complete.

`ARCHITECTURE.md` remains authoritative at v3.20. It already records the durable profile-qualified snapshot contract, public-source/deployment separation, bounded PREPARE behavior, source-only handoff, immutable lineage and REVIEW ceiling proven by this acceptance; no further architecture revision is required.

`DESIGN-SYSTEM.md` was not changed because this work did not alter durable visual or interaction-system rules.

`PROJECT-CONSTITUTION.md` was not changed because the release exercised existing least-privilege, explicit-authority, immutable-lineage and REVIEW-ceiling principles rather than introducing a new constitutional rule.
