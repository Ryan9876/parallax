from pathlib import Path

p = Path('CURRENT-STATE.md')
text = p.read_text()

old_status = 'P2-V0.23.31 EXPLICIT EXECUTION CONTRACT + END-TO-END ACCEPTANCE REPLAY PRODUCTION-DEPLOYMENT-VERIFIED / PRE-USER CANDIDATE CANARY VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING**'
new_status = 'P2-V0.23.31 EXPLICIT EXECUTION CONTRACT + END-TO-END ACCEPTANCE REPLAY PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED / P2-V0.23.32 BOUNDED CANDIDATE VALIDATION REPAIR + EXPLICIT CANARY IDENTITY PRODUCTION-DEPLOYMENT-VERIFIED / PRE-USER CANDIDATE CANARY VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING**'
if text.count(old_status) != 1:
    raise SystemExit('top-level P2-V0.23.31 status marker drifted')
text = text.replace(old_status, new_status, 1)

old_heading = '## P2-V0.23.31 — explicit execution contract and end-to-end acceptance replay — PRODUCTION-DEPLOYMENT-VERIFIED / PRE-USER CANDIDATE CANARY VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING'
new_heading = '## P2-V0.23.31 — explicit execution contract and end-to-end acceptance replay — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED'
if text.count(old_heading) != 1:
    raise SystemExit('P2-V0.23.31 heading drifted')
text = text.replace(old_heading, new_heading, 1)

old_boundary = 'The deterministic pre-user acceptance replay has therefore crossed the same real disposable candidate BUILD/TEST/VERIFY substrate that previously required a signed-in user retry to discover post-generation blockers. No Project, Engineering Run, source lineage, Git, delivery, lifecycle, deployment or REVIEW state was mutated by the canary. The remaining P2-V0.23.31 completion boundary is authenticated real-path acceptance: a signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` (or equivalent exact marker-free greenfield work) must enter disposable BUILD/TEST/VERIFY under the persisted execution contract or expose a later bounded blocker. Workstream #539 remains open until that evidence exists.'
new_boundary = 'Authenticated real-path acceptance for P2-V0.23.31 is complete under the workstream’s explicit later-bounded-blocker alternative. On exact production deployment `dpl_FDuJ3JKRHnvHf14mzJX59cVGasAY`, the signed-in retry of Engineering Run `3a1ba66a-5649-42b6-81ee-91684fe06bbc` restored normal session ownership, resumed the protected path, read authoritative source lineage, created and exercised a real disposable Vercel candidate sandbox, and reached protected candidate BUILD under the persisted `static-web-v1` execution contract. Production emitted `parallax_candidate_validation_failed candidate=candidate-primary stage=BUILD timed_out=False` before durable IMPLEMENT failure sequence #89. The prior `VALIDATION_PROFILE_ERROR` did not recur. This proves the explicit execution-contract and real candidate-validation boundary is active and exposes a genuinely later bounded blocker: repairable candidate-authored static-web BUILD failure was still terminal rather than consuming the already-bounded alternative-candidate slot. Workstream #539 is closed completed; successor #543 / P2-V0.23.32 owns bounded validation-guided replacement.'
if text.count(old_boundary) != 1:
    raise SystemExit('P2-V0.23.31 acceptance boundary paragraph drifted')
text = text.replace(old_boundary, new_boundary, 1)

anchor = '## P2-V0.23.30 — source-anchored candidate validation profile — PRODUCTION-BEHAVIOR-ACCEPTED / LATER BOUNDED BLOCKER EXPOSED\n'
if text.count(anchor) != 1:
    raise SystemExit('P2-V0.23.30 insertion anchor drifted')
section = '''## P2-V0.23.32 — bounded candidate validation repair and explicit canary contract identity — PRODUCTION-DEPLOYMENT-VERIFIED / PRE-USER CANDIDATE CANARY VERIFIED / AUTHENTICATED REAL-PATH ACCEPTANCE PENDING

Workstream: #543. Release PR: #544. Governing specification: `P2-V0.23.32`. Architecture: `ARCHITECTURE.md` v3.43.

P2-V0.23.32 converts one repairable `static-web-v1` disposable candidate BUILD/TEST/VERIFY rejection into a single bounded validation-guided replacement while preserving the existing two-candidate ceiling. Only an exact one-line reason from the server-owned static-web validator’s closed vocabulary can become `validation_reason_code`; only candidate-authored content/structure reasons are repairable. The rejected candidate is discarded, the replacement consumes the existing second candidate / alternative-round capacity, starts again from authoritative accepted/base source under the same approved Work Specification and immutable PLAN-bound execution contract, and reruns unchanged proposal safety, SafeImplementationEngine, real disposable BUILD/TEST/VERIFY, independent evaluation and routing. A second validation rejection is terminal and cannot create a third candidate. Raw validator output, rejected source/generated content, exception/provider payloads, filesystem roots, credentials and environment values remain excluded from repair guidance and durable evidence. If validation repair consumes the second candidate slot, ordinary competitive challenger creation is skipped. Model/provider roster, 60-second hosted timeout, zero hidden provider retries, validator-repair budget, source-lineage authority, Git/deployment/lifecycle authority and the human REVIEW ceiling remain unchanged.

Validated release and deployment evidence:

- corrected protected DSPy SpecCritic + SpecCompiler preparation `33458383302`: SUCCESS;
- focused implementation and regression validation `33459028277`: SUCCESS;
- architecture v3.43 reconciliation and governed-spec revalidation `33465359072`: SUCCESS;
- exact green PR head: `1db8760f8c2ab448c1bea6576b73a37ec7039d99`;
- PR #544 Bounded Autonomy Pilot `33465602604`: SUCCESS;
- PR #544 Workstream Spec Validation `33465602578`: SUCCESS;
- PR #544 Parallax P2 CI `33465602587`: SUCCESS, including API regression, client checks, protected promotion evaluation and committed DSPy release evidence;
- squash merge / exact application source: `421b81113a0bbe27df7a312ceec49cdc2c55899b`;
- post-merge Workstream Spec Validation `33465737419`: SUCCESS;
- post-merge Parallax P2 CI `33465737383`: SUCCESS, including full API regression, client checks, protected promotion evaluation and fresh promotion-boundary DSPy SpecCritic/SpecCompiler compilation and verification;
- production API deployment `dpl_BgLMFQY3k2q1ZSF3yL6bjJbCedCs`: target production, state `READY`, exact application source `421b81113a0bbe27df7a312ceec49cdc2c55899b`, region `iad1`, canonical alias `parallax-api-tan.vercel.app`;
- production build preflights passed provider/private Blob, exact delivery permission, projected source (700 lineage-eligible files / 7,261,577 UTF-8 bytes), private Blob SDK, lineage composition, agentic runtime, projected bootstrap, execution snapshots and Engineering Run event schema guard;
- production candidate-validation canary: PASS through real disposable `BUILD`, `TEST`, and `VERIFY`, explicitly reporting `contract=static-web-v1`, `binding=GREENFIELD_STATIC_WEB`, `ecosystem=static-web`, `profile=node-v1`, `stages=BUILD,TEST,VERIFY`, candidate digest `f2e8320d210228539bd8c44a9a2d62dccea66d4e7d29f81389b71ba148a483a4`;
- production `/health`: HTTP 200;
- production `/ready`: HTTP 200 with database/providers ready and one provider target;
- exact deployment warning/error/fatal runtime scan after readiness was clean.

The release is therefore deployment-verified and its deterministic real-sandbox static-web canary is green on the exact production source. The remaining P2-V0.23.32 completion boundary is authenticated real-path behavior acceptance. Trusted QA may exercise an equivalent exact marker-free greenfield run through the dedicated QA OIDC session and ordinary production endpoints; this is allowed because it preserves the same product/session ownership boundaries rather than bypassing them. Acceptance requires the prior terminal primary BUILD pattern to recover through the bounded replacement and advance canonical IMPLEMENT, or to expose a genuinely later bounded blocker. Repeating the same unrepaired primary BUILD failure does not pass. Workstream #543 remains open until that evidence exists.

No database migration, generic Node/Python ecosystem admission, arbitrary repository command path, new provider/model/credential, retry-budget increase, hosted timeout increase, hidden provider retry, source-lineage authority expansion, Git/deployment authority expansion, lifecycle-transition authority expansion, automatic REVIEW completion or UI redesign was added.

'''
text = text.replace(anchor, section + anchor, 1)
p.write_text(text)
