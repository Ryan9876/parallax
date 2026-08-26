# Parallax 2.0 Current State

Date: 2026-08-26

Status: **WAVE 5 RELEASED / PRODUCTION STABILIZATION THROUGH #127 DEPLOYMENT-VERIFIED / CLIENT READY / API READY / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / NEXT CAPABILITY PHASE NOT YET AUTHORIZED**

## Current production truth

Parallax is running the deployment-verified Wave 5 generalized application-delivery platform plus bounded production stabilization completed through issues #246, #244, #245, #252, #130, #243, and #127.

The production state is intentionally component-specific:

- repository `main` currently points at merge `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5`;
- production client deployment `dpl_642fFKXWzZfA7pkezAYrJbuANXZn` is `READY`, target `production`, exact Git SHA `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5`, with `aliasError=null`;
- production client aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`;
- production API remains deployment `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`, `READY`, target `production`, application/API Git SHA `5ec7eabc046b9995c8d11d5081df15b986a558fe`, with `aliasError=null`;
- production API aliases include `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`.

The API Git SHA is intentionally older than repository/client `main`: hotfixes #243 and #127 are client-only. Their corresponding API production builds were canceled as non-app-affecting rather than replacing the deployment-verified API runtime.

Post-cutover verification after #127 established:

- canonical production client root returned HTTP 200;
- client deployment-scoped `error`/`fatal` runtime log query returned no entries after cutover;
- API `/health` returned HTTP 200 with `status=ok`;
- API `/ready` returned HTTP 200 with database/providers healthy and one registered provider target;
- the API release remains fail-closed for unauthenticated access as previously verified.

## Most recent production stabilization

### #127 — authenticated session expiry returns to login gate

Issue #127 is **closed / released / production deployment-verified**.

The defect was client-local: after the server session expired, generic authenticated API requests could return 401 while the hosted browser still displayed the ready workspace. Server authentication itself was already fail-closed.

Exact candidate `214320ffa88e8657ee4ff12dfeb864dfe7b849db` adds a client-local authentication-required signal, emits it from authenticated 401 handling, and has `WebAuthRoot` consume it only after the hosted application is already in `ready`. The root then clears the displayed profile/workspace and returns to the Google login gate. Initial session resolution, Google callback exchange, authorization-denied handling, explicit sign-out, server authentication, session lifetime, credential handling, provider authority, and deployment authority are unchanged.

Exact-head validation:

- Bounded Autonomy Pilot #574 / run `32989109244` — success;
- Parallax P2 CI #941 / run `32989241379` — success;
- full API regression and contract checks — success;
- client typecheck/state/export — success;
- browser/Skia acceptance including the deterministic session-expiry regression — success;
- protected Code/Engineering/Reason promotion and regression rejection — success;
- DSPy release compilation/verification — success;
- exact-head Vercel Preview `dpl_GQ8TDjV7JqGf7TaodmZq7iQuTAJ5` — `READY`.

PR #258 merged with expected-head protection as `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5`. Production client `dpl_642fFKXWzZfA7pkezAYrJbuANXZn` is `READY` on that exact merge SHA. The non-app-affecting API build `dpl_J9hhDh73beZAsPQ3dHb3Mko4WYUo` was canceled as expected.

Immediate client rollback is the previous deployment-verified #243 client `dpl_7CgqtEFDtFpd7xDWxftSwZd9FdiL` at merge `fc0ba781bab65fb795ddc5695f14cd7e7f524805`.

### #243 — explicit new-objective recovery after specification amendment

Issue #243 is **closed / released / production deployment-verified**.

The server-owned `SPEC_AMENDMENT` guard was correct but the compact/mobile client made the expected boundary look like a failed run. The correction preserves the fail-closed guard and adds an explicit `Start new objective` action. Code mode routes that action through the existing canonical Project compatibility resolver, creates a genuinely fresh conversation, and inherits no approved Work Specification or Engineering Run.

Exact candidate `2d236ca6f3d631d6697e68475125ea681aa4f8d6` passed Bounded Autonomy Pilot #569 / run `32986842431`, P2 CI #935 / run `32986842435`, browser/Skia acceptance, protected promotion/regression evaluation, DSPy release compilation, and exact-head Vercel Preview `dpl_HU7mTbpyQEAbTpbekpf1NemPFHGJ` before PR #257 merged as `fc0ba781bab65fb795ddc5695f14cd7e7f524805`.

Production client deployment `dpl_7CgqtEFDtFpd7xDWxftSwZd9FdiL` reached `READY` on that exact merge SHA with `aliasError=null`; the API build was canceled as non-app-affecting.

### #130 — GitHub repository casing mismatch

Issue #130 is **closed / deployment-verified / operator functional retest passed**.

The production target resolver and installation-scope verifier previously compared GitHub owner/repository identity case-sensitively even though GitHub repository identity is case-insensitive. The correction case-folds only the GitHub owner/repository identity at those comparison boundaries while preserving persisted Project identity, repository IDs, Vercel refs, credentials, lineage, tool authority, and production authority.

Production merge `23678383a0a97dfc3df4feadecba507eb290f6ae` and API deployment `dpl_7Pk1j3oBe3YvgcbRunP9JF8yBzVZ` were deployment-verified. The later operator run using persisted `github:ryan9876/parallax` successfully crossed SPECIFY and PLAN and reached IMPLEMENT, satisfying the functional-retest closure criterion. Its later IMPLEMENT failure was a distinct stabilization issue and not a casing regression.

## Earlier Wave 5 production stabilization retained in the baseline

### #246 — fresh Code objective handoff

A fresh ACTIVE Code conversation with no prior durable objective now persists its first objective exactly once and hands off deterministically to Work Specification capture instead of invoking model-backed prior-scope comparison. Protected scope classification still applies to established Code follow-ups and Reason mode. No Work Specification, approval, Project, Engineering Run, mutation, provider, REVIEW/HUMAN_REQUIRED, or deployment authority was broadened.

Exact candidate `7eaa290fd57a2a333976ed882f29075f9d022e3f` passed the governed release gates before merge `36548611c3806d08d6fbfcdb686fe2a025956194`; production API `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB` was deployment-verified. Operator retest later passed.

### #244 — canonical repository target enforcement

The selected Project repository is rechecked at Work Specification approval and Engineering Run activation so execution cannot silently drift to a different repository target. Exact candidate `40f8bc25fcfad6c725a666cf236c6ffda2402991` passed Workstream Spec Validation #357, Bounded Autonomy #563, and P2 CI #924 before merge `e818bc9f44e473195a1bfd7f82b3c0cb3abf7e42`; production API `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81` was deployment-verified.

### #245 — durable IMPLEMENT failure truthfulness

Sanitized pre-mutation IMPLEMENT failures now project append-only durable failure evidence and the Live Build client falls back to authoritative FAILED/resume-stage state without fabricating worker/source/provider/preview/evaluation success. Exact candidate `7aebfb65d46df57ed38031d3e213a27dc9fe6303` passed Bounded Autonomy #564 and P2 CI #926 before merge `464aa9f106348638cfd436aa427398edbd3e1583`; production API `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and client `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm` were deployment-verified.

### #252 — retryable Work Specification provider rate limiting

When every configured Work Specification model route returns sanitized `LMRateLimitError`, Parallax now reports an explicit retryable capacity state while preserving `SPEC · NOT CAPTURED`. It does not invent a Work Specification, fabricate a `Retry-After` duration, alter provider/model/credential authority, or claim external OpenAI API capacity has recovered.

Exact candidate `a9c5a6c941c596081202b3bc4dfa8f4d8fefb4d3` passed Workstream Spec Validation #359, Bounded Autonomy #565, P2 CI #928, full API/client/browser/evaluation/DSPy release gates, and both Vercel checks before merge `5ec7eabc046b9995c8d11d5081df15b986a558fe`.

Production API `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` and then-current client `dpl_DwjTqyD5BZSGf6XAexZzg42enBQf` were deployment-verified on that exact merge SHA. The API deployment remains the current production API after the later client-only #243/#127 releases.

## Wave 5 generalized application-delivery baseline

Control Tower #215 completed all six Wave 5 workstreams:

1. #216 / `P2-V0.18.1` — Repository Intelligence & Compatibility;
2. #217 / `P2-V0.18.2` — Governed Skills Runtime;
3. #218 / `P2-V0.18.3` — Application Service Bindings;
4. #219 / `P2-V0.18.4` — Objective-to-Application Orchestration;
5. #220 / `P2-V0.18.5` — Validated Engineering Memory & Reuse;
6. #221 / `P2-V0.18.6` — Generalization Benchmark & Integrated Reference Proof.

Final Wave 5 release candidate `2fb01805ba612228d116ca4c4d8d0980d7886007` passed Workstream Spec Validation #350, Bounded Autonomy #552, P2 CI #909, full API regression, browser/Skia acceptance, protected Code/Engineering/Reason promotion and regression rejection, release DSPy compilation/plan verification, and both Vercel release checks before expected-head PR #241 merged as `c39b5352be940f4052baa65c7cdd9d7c3ec773bb`.

Wave 5 established production-ready bounded repository intelligence, exact-digest governed skills, Project-scoped logical service bindings with opaque secret slots, objective-to-application orchestration, private-by-default validated engineering memory, and a permanent multi-shape generalization proof. Repository/source/model content remains evidence rather than authority, fresh validation remains mandatory, and `REVIEW` / `HUMAN_REQUIRED` remains the autonomous ceiling.

## Rollback

Current immediate rollback references:

- client: #243 deployment `dpl_7CgqtEFDtFpd7xDWxftSwZd9FdiL` at merge `fc0ba781bab65fb795ddc5695f14cd7e7f524805`;
- API: #245 deployment `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` at merge `464aa9f106348638cfd436aa427398edbd3e1583` remains the most recent prior full API/client pair, while the current API `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` is deployment-verified and unchanged by #243/#127.

Earlier known-good Wave 5 and stabilization deployments remain available. Rollback remains non-destructive and follows the existing governed release/flag-first policy.

## Program control state

- Control record #31 remains open and active.
- Roadmap #32 remains open as the durable program record.
- Waves 1–5 are complete and Wave 5 is production deployment-verified.
- Production stabilization through #127 is deployment-verified.
- There is **no authorized Wave 6 or successor capability phase** in the current control state.
- Verified production defects may continue through the existing bounded hotfix/recovery process.
- New planned capability work requires an explicit evidence-based objective plus a new Control Tower/workstream boundary.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity, and accepted lineage remain server-owned;
- deterministic/protected validation outranks model judgment;
- repository/source/model content is evidence, not authority;
- single-writer mutation authority and immutable accepted lineage remain authoritative;
- correction cannot weaken acceptance/evaluation policy;
- skills, service bindings, repository intelligence, and validated memory cannot create execution/provider/deployment/approval authority;
- cross-Project privacy boundaries remain strict;
- no silent repository switching, credential refresh, session extension, approval, merge, or deployment authority is introduced by the stabilization work;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous ceiling;
- no deployment is recorded as production-verified without exact-head release evidence and post-cutover verification.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.1 — unchanged; the stabilization work restores or clarifies existing contracts rather than changing durable architecture.
- `DESIGN-SYSTEM.md` — unchanged; no durable visual-language change was introduced.
- `CURRENT-STATE.md` — updated by this reconciliation because production deployment state materially changed.

This `CURRENT-STATE.md` update is a **record-only repository change**. When merged, its documentation merge SHA must not be treated as a new application/runtime deployment identity. Production client remains `dpl_642fFKXWzZfA7pkezAYrJbuANXZn` at application merge `8065d124145686e6a93cfdc6c4b2cec4dfc3f5a5`; production API remains `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` at application/API merge `5ec7eabc046b9995c8d11d5081df15b986a558fe`.