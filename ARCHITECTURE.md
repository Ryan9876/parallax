# Parallax 2.0 Architecture

Version: 3.29
Status: Authoritative

## Version relationship

Architecture v3.29 moves standing production-QA execution identity to a dedicated repository trust boundary. GitHub Actions OIDC authorization is now an exact server-owned `(repository, repository_id, workflow_ref)` tuple, binding the human-readable repository identity to GitHub's stable repository ID and the exact workflow reference. This prevents workflow substitution, cross-repository replay, and silent trust inheritance if a repository name is later deleted and recreated. The migration admission release temporarily retains the two existing exact application-repository QA tuples until the dedicated `Ryan9876/parallax-qa` production replay is behaviorally proven; the bounded QA principal, issuer, audience, main ref, hosted-runner requirement, allowed events, Project / Work Specification / Engineering Run authority, source lineage, model routing, Git/deployment authority, and REVIEW ceiling are unchanged.

Architecture v3.28 makes hosted model-routing failure semantics truthful at the provider/output boundary: a provider-successful implementation proposal that fails strict server-owned JSON/schema decoding is validation failure, while transport, configuration, rate-limit and unrelated attempt exceptions remain provider failure. The implementation proposal prompt states the exact already-enforced JSON keys more explicitly, but parsing remains strict and fail-closed. Architecture v3.27 remains the recovered-worker PLAN-rebinding foundation, v3.26 remains the failed-IMPLEMENT PLAN-refresh foundation, v3.25 remains the terminal-worker re-arm foundation, v3.24 remains the hosted model escalation foundation, v3.23 remains the validator-guided repair foundation, v3.22 remains bounded implementation-candidate recovery, and v3.21 remains empty-greenfield source authority. The complete v3.19 architecture is incorporated by reference. Every v3.19 durable contract not explicitly changed below remains authoritative, including source/deployment separation, canonical Project / Work Specification / Engineering Run authority, immutable accepted source lineage, single-writer canonical mutation, durable worker recovery, Project-scoped tool/provider authority, protected evaluation, logical workspace deletion/retention, Preview/REVIEW ceilings, governed release evidence, W8-S2 deferred Vercel Project readiness, W9 benchmark admission, governed skill intake, explicit GitHub installation coverage, exact-one-repository runtime credential scope, quota-independent public source bootstrap, repository-aware protected validation, and bounded dependency PREPARE.

Architecture v3.19 removed GitHub's shared anonymous REST quota from the normal public-source bootstrap path. Public source authority remains established through GitHub's unauthenticated Git smart-HTTP advertisement and an exact commit-addressed source archive. Public-source throttling or provider failure does not silently construct a deployment-provider credential path.

This revision replaces the assumption that every admitted validation ecosystem can use one common execution snapshot. Snapshot selection is now finite, server-owned, and bound to the deterministic validation profile selected from exact source. The established Python path retains the common snapshot; the reserved Node profile identity maps to that same common snapshot without changing generic Node's existing fail-closed source admission; admitted `.NET` requires a dedicated prequalified source-free snapshot and never falls back to the common image.

## Dedicated production-QA repository trust boundary

Architecture v3.29 treats a GitHub Actions QA identity as one exact repository-name/repository-ID/workflow tuple. Production authorization never accepts those claims independently: all three signed OIDC claims must match the same server-owned allowlist entry. Standing dedicated QA is repository `Ryan9876/parallax-qa`, stable GitHub repository ID `1351817336`, with exact workflow `Ryan9876/parallax-qa/.github/workflows/production-replay.yml@refs/heads/main`. The temporarily retained application-repository identities are repository `Ryan9876/parallax`, stable GitHub repository ID `1340272514`, plus their exact already-admitted workflow references.

Binding stable repository ID closes owner/name reuse as an authentication path: deleting and recreating a repository at the same name yields a different repository ID and therefore fails closed until explicitly reviewed. A correct repository ID with the wrong owner/name, a correct owner/name with the wrong ID, or either identity with an unpaired workflow is rejected.

The remaining identity guards stay conjunctive and fail-closed: issuer `https://token.actions.githubusercontent.com`, audience `parallax://qa-production`, ref `refs/heads/main`, GitHub-hosted runner, admitted `workflow_dispatch` or `push` event, and a bounded non-empty GitHub run ID. Actor identity alone never grants access. No prefix, glob, substring, branch-only, event-only, owner/name-only, repository-ID-only, or workflow-only match creates QA authority.

The dedicated workflow authenticates only to the existing bounded QA principal. It cannot inherit normal-user ownership or create source-publication, Git mutation, deployment, production-promotion, lifecycle-transition, or REVIEW-completion authority beyond the product APIs already available to that bounded QA account. Routine standing acceptance is source-only Python plus OT Time/.NET replay to REVIEW and authenticated ZIP handoff. W9-S1 greenfield initialization is not standing QA trust and requires a separately reviewed exact workflow when a fresh approved target exists.

Cutover is intentionally staged. During P2-V0.23.17 only, the two prior exact `Ryan9876/parallax` workflow pairs remain admitted alongside the new dedicated pair so the new path can be production-proven without destroying rollback. After successful dedicated-repository replay, a follow-up trust-contraction release removes the old pairs and workflow files. Temporary dual trust is migration evidence, not a permanent expansion target.

## Source authority is independent from deployment authority

A canonical Project repository binding identifies the source context. It does not select or imply a deployment provider.

For GitHub source bootstrap, Parallax has two bounded read paths:

1. **Verified public source read** — the unauthenticated Git smart-HTTP `git-upload-pack` advertisement must expose the canonical repository HEAD and default-branch symref. Parallax pins the advertised immutable commit and reads source only from the exact commit-addressed GitHub codeload archive. The archive is bounded by member count, compressed/uncompressed source limits, path normalization, secret-sensitive path projection, regular-file-only semantics, UTF-8 source validation, and exact revision identity. This path has no bearer credential, does not call `api.github.com`, and exposes only repository-resolve, tree-read, and file-read actions.
2. **Exact-repository credentialed read** — a repository not visible to the public source transport retains the existing short-lived exact-repository credential path and the `REPOSITORY_AUTHORIZATION_REQUIRED` consent boundary established by v3.16.

Public-source authority cannot create a branch, commit, pull request, repository, deployment, provider project, secret, environment variable, alias, domain, merge, or production promotion. A public-source timeout, malformed response, throttling response, or provider outage remains a typed public-source failure; it does not reclassify the repository as private and does not trigger a Vercel-backed credential fallback. Only `REPOSITORY_NOT_FOUND` may enter the existing credentialed repository path.

This separation means a public Project can bootstrap PLAN without GitHub anonymous REST capacity, Vercel Connect, a Vercel Project, or a Vercel Preview target. Private source remains fail-closed when exact repository authority is unavailable.

## Project delivery policy

Deployment is an explicit server-owned Project policy. Initial durable modes are:

- `source-only` — protected engineering produces and verifies accepted source lineage; at REVIEW Parallax records an exact replay-safe handoff and allows authenticated download of that accepted lineage. No hosting-provider readiness or deployment request is made.
- `vercel-preview` — the existing bounded GitHub publication plus Vercel Preview path remains in force, including exact target/source identity, READY Preview evidence, and the existing Preview/REVIEW ceiling.

Projects created before explicit delivery policy are migrated to `vercel-preview` so established behavior does not change silently. New Projects default to `source-only`; Vercel is selected deliberately when wanted.

A Project delivery mode may change only before implementation begins. `SPECIFY` and `PLAN` are the mutable window. Once any active Engineering Run has entered `IMPLEMENT` or a later non-terminal protected stage, a different delivery mode is rejected. Reasserting the already-selected mode is idempotent.

Future IIS, local, Azure, AWS, Cloudflare, container, or other delivery adapters must attach at this delivery seam. They must not change canonical source authority, Engineering Run semantics, accepted-lineage validation, or the REVIEW ceiling merely to support another deployment target.

## Source-only handoff boundary

`source-only` is not a bypass around protected engineering. Handoff is available only after the ordinary run has reached REVIEW with accepted IMPLEMENT and VERIFY evidence bound to the same exact source lineage.

The durable handoff record contains bounded Project, run, repository-identity digest, accepted lineage, content digest, delivery mode, and deterministic handoff identity. It contains no source bytes, provider bearer tokens, cookies, OIDC tokens, storage credentials, arbitrary provider payloads, or raw private-object URLs.

Authenticated download reconstructs the exact recorded lineage from Parallax's durable lineage store, verifies Project/run/lineage/content identity, validates every path, size and SHA-256 digest, rejects symlink/path escape, enforces a bounded total package size, and returns a private no-store ZIP. Internal lineage storage may remain implemented on Vercel Blob; that infrastructure choice does not make the generated application a Vercel deployment.

Source-only observability is also distinct from Vercel delivery. Successful source handoff is projected as a `SOURCE_DELIVERY` event under the `SOURCE_LINEAGE` subsystem with zero provider actions and the deterministic handoff ID. It must not claim a GitHub publication or Vercel Preview occurred.

## Greenfield GitHub repository authority

Parallax continues to treat **provider installation coverage** and **runtime repository-token scope** as separate authority layers for credentialed repositories.

A canonical Project may bind a GitHub repository that is not yet covered by the approved `github/parallax-runtime` Vercel Connect / GitHub App installation. Repository identity by itself is not authorization. For a repository that requires credentials, provider installation coverage must have explicit coverage for the exact canonical repository before the credentialed source path may proceed.

Installation coverage may be narrow to one repository or may cover multiple repositories when the GitHub account or organization owner explicitly chooses that broader installation scope. Parallax must never silently broaden provider installation coverage.

### Exact runtime token scope remains mandatory

Broader installation coverage does not create broader runtime authority. Every credentialed Engineering Runtime exchange remains short-lived and requests exact repository authorization through Vercel Connect `authorizationDetails` for the canonical Project repository.

A derived GitHub credential is accepted only after provider read-back proves it can see **exactly one repository** and that repository matches the canonical Project binding. A token that can see multiple repositories, the wrong repository, or an ambiguous scope fails closed with the existing scope-mismatch semantics.

### Repository authorization readiness

When Vercel Connect returns HTTP 422 for an otherwise valid exact-repository `github_app_installation` authorization request, Parallax classifies the condition as `REPOSITORY_AUTHORIZATION_REQUIRED` rather than collapsing it into a generic credential-unavailable failure.

That classification applies to the credentialed path. It does not prevent a repository that is anonymously cloneable through GitHub's public Git transport from using the separate credential-free read-only bootstrap path.

Timeouts, network failures, provider 5xx responses, missing runtime OIDC, malformed token responses, expiry failures, and unrelated credential failures retain their existing fail-closed classifications. They must not be mislabeled as repository-consent requirements.

### Mutation and lifecycle ceiling

Neither public readability nor repository installation coverage grants source mutation or deployment authority.

- public source reads never authorize GitHub writes;
- missing credentialed repository authority never triggers silent installation widening;
- source-only delivery never creates a Vercel Project or Preview;
- Vercel delivery still requires its existing explicit readiness and exact-target checks;
- no path grants production promotion, domain/environment administration, Engineering Run transition authority, or REVIEW completion authority.

## Empty-greenfield lineage and REVIEW-only repository initialization

Architecture v3.21 adds a narrow source-root state for a canonical GitHub repository that is positively proven empty under exact repository authority. A public/source error, 404/403 ambiguity, provider outage, malformed response, or missing credential never creates greenfield authority. The runtime first preserves the existing public/credentialed commit-bearing bootstrap. Only when no durable root exists may a typed authenticated `repository.inspect` distinguish a positively empty canonical repository from ordinary failure.

A greenfield durable root is explicit and unique: `source_kind=greenfield`, no parent, zero files, zero bytes, the canonical empty content digest, and non-null provenance/source-reference digests bound to the canonical repository and default branch. Ordinary repository/template/starter roots remain non-empty. IMPLEMENT must produce a changed non-root lineage containing at least one protected source artifact before protected BUILD/TEST/VERIFY can succeed.

Repository initialization is not PLAN authority. PLAN through VERIFY performs no GitHub mutation merely to make an empty repository usable. Only after accepted source has passed VERIFY and the run reaches REVIEW may Vercel-Preview delivery invoke the separate server-owned `repository.initialize-empty` mutation capability. That capability reuses the already readiness-qualified short-lived exact-repository GitHub credential but is isolated from the ordinary branch/commit/PR capability registry.

GitHub REST cannot create the first ref in an empty repository. The released initializer therefore follows the provider-supported Contents API sequence: create one fixed non-executable `.parallax-greenfield` bootstrap marker with deterministic server-owned actor/message/content and a one-way provenance digest; serially delete that exact returned blob on the canonical default branch; then read back and prove the resulting head tree is empty. Replay is accepted only when the current cleanup head, its single bootstrap parent, both messages/actors, the fixed marker path/content/provenance, empty head tree, parent count, and default ref match exactly. An unrelated head or concurrent change fails closed; no force update occurs.

The temporary marker exists only in immutable initialization history and is absent from the default-branch head before application source publication. Accepted source is then published through the existing bounded Parallax branch -> accepted-lineage commit -> pull request -> Vercel Preview path and remains capped at REVIEW. Source-only delivery never invokes this Vercel-Preview repository initializer and remains independent from application deployment.

Repository installation consent remains an explicit provider/user boundary. The production runtime exposes the bounded `REPOSITORY_AUTHORIZATION_REQUIRED` code and preserves same-run retry, but v3.21 adds no provider-consent endpoint, PAT, reusable Vercel account token, GitHub user token, browser-supplied provider credential, or Preview authority widening. Runtime readiness after external consent remains ordinary Connect token exchange plus exact-one-repository scope verification.

## Human-authorized refreshed-PLAN worker binding

Architecture v3.27 preserves worker checkpoint `plan_ref` immutability as the default rule and adds one narrowly derived exception required to make the v3.26 explicit failed-IMPLEMENT PLAN refresh internally coherent. A historical worker checkpoint is never rewritten merely because current orchestration policy changed.

A changed worker `plan_ref` is admissible only when authoritative Engineering Run attempt history proves the latest complete refresh cycle: a persisted `PLAN / RESUMED` control attempt contains server-authored `plan_refresh_authorized=true`, and a later protected `PLAN / PASSED` attempt contains a valid server-owned `team_plan_id`. The incoming checkpoint must equal exactly `agentic-plan:<team_plan_id>` from that successful refreshed PLAN. Browser/request parameters, model output, repository content, worker-local flags, and exception strings cannot create or select this authority.

A newer refresh control immediately invalidates any prior derived replacement authority until a later protected PLAN passes. A missing, false, malformed, incomplete, arbitrary, or historical PLAN reference fails closed. Engineering Run PLAN attempts are consumed in their durable ordered attempt relationship, so refresh-cycle interpretation is deterministic.

The first accepted checkpoint under the refreshed PLAN persists that new `plan_ref`; ordinary checkpoint equality then becomes authoritative again. Another change requires another complete explicit human-authorized refresh cycle. Historical PLAN attempts, run events, worker events, checkpoint revisions, source-lineage evidence, and lease-generation history remain preserved.

This rule grants no additional lease, reassignment, retry, source mutation, source-lineage acceptance, Git/provider, deployment, approval, or REVIEW authority. Existing Work Specification binding, source-lineage equality, bounded worker recovery, candidate recovery, model-routing, validation, and REVIEW ceilings remain unchanged. No database migration or public API field is introduced.

## Human-authorized terminal-worker re-arm

Architecture v3.25 distinguishes an explicit human recovery decision from automatic worker restart. A durable worker execution that has reached terminal `FAILED` remains fail-closed for ordinary acquisition, client reconnect, page refresh, or a direct autonomous-execution request. Terminal state is not silently converted into another attempt.

When the authenticated Engineering Run state machine successfully resumes a run that was authoritatively `FAILED`, that persisted resume boundary may prepare the same run's unleased terminal worker for one new bounded generation. Preparation is a compare-and-swap transition from `FAILED` to `RECOVERING`; it preserves worker identity, checkpoint payload and revision, current step, accepted and last-known-good source-lineage references, and lease-generation history. It resets only worker-local retry/no-progress/oscillation counters and progress fingerprints, clears the prior terminal stall/blocker markers from current worker state, and records `REASSIGN` as the next protected recovery action. Historical Engineering Run attempts, events, failures, checkpoints, and lineage evidence remain immutable observation.

The preparation step does not issue a mutation lease. The existing protected `RECOVERING -> REASSIGNED` path remains the sole path that increments worker lease generation and grants the fresh bounded mutation lease. Replayed resume preparation is idempotent once the worker is no longer `FAILED`, so concurrent or repeated requests cannot manufacture multiple generations. `PAUSED`, `HUMAN_REQUIRED`, `READY_FOR_INTEGRATION`, and `SUCCEEDED` worker boundaries are not widened by this rule.

Candidate generation within the newly authorized worker generation remains subject to the existing finite admitted-agent sequence, `max_reassignments_per_work_unit`, validator-guided repair, protected proposal and candidate validation, source-lineage acceptance, Git/provider/deployment authority, and the REVIEW ceiling. A later terminal failure requires another explicit human resume; v3.25 introduces no automatic cross-attempt retry loop.

## Structured-output validation routing boundary

Architecture v3.28 distinguishes provider execution from protected structured-output validation. A hosted model request can complete successfully at the provider boundary and still return output that cannot be decoded into the exact server-owned `ImplementationProposal` schema. That condition is not provider unavailability.

Implementation-generation programs may therefore raise one typed server-owned `ModelOutputValidationError` only after a provider result exists and strict protected proposal JSON/schema validation fails. The exception carries no raw model output, validation payload, repository text, provider response, secret, or arbitrary exception message. `ModelRouter` catches that type before its generic provider boundary and records the attempt as `validation_failed`. The existing validator-returned-false path remains `validation_failed` as well.

Transport, configuration, rate-limit and unrelated program exceptions continue through the generic sanitized provider boundary and remain `provider_failed`, retaining only exception class in bounded attempt evidence. If every configured attempt is validation failure, routing remains `VALIDATION_EXHAUSTED`; if every attempt is `provider_failed / LMRateLimitError`, routing remains `RATE_LIMITED`; mixed provider and validation outcomes remain conservatively `PROVIDER_EXHAUSTED`. Exception strings and model text never determine the classification.

The implementation proposal prompt now states the exact already-enforced JSON keys and forbids Markdown/prose wrappers more explicitly. This is generation guidance only. Parallax does not strip fences, extract prose, repair JSON, accept extra keys, relax acceptance coverage, or bypass strict Pydantic and safe-patch validation. Hosted order remains `Luna -> Terra -> Sol`; candidate recovery, worker recovery, reassignment ceilings, source mutation, lineage, Git/provider/deployment authority and REVIEW boundaries are unchanged.

## Server-owned hosted model escalation

Architecture v3.24 separates implementation-agent identity from model-selection priority. `AgentIdentity.digest` remains a cryptographic identity/integrity value only; lexical SHA-256 order has no economic or capability meaning and cannot select which hosted model runs first.

The admitted roster carries bounded server-owned `selection_priority` metadata. Roster canonicalization orders agents by `(selection_priority, identity_digest)`, so equivalent priority values retain deterministic digest tie-breaking while explicit priority controls selection. Priority is serialized into admitted-roster evidence and therefore changes the roster digest and orchestration plan identity when policy changes. Browser input, repository content, model output, and provider responses cannot supply or alter this value.

The released hosted implementation order is `openai/gpt-5.6-luna` first, `openai/gpt-5.6-terra` second, and `openai/gpt-5.6-sol` last. The smallest-capable-team rule remains authoritative: a serial equal-capability implementation unit selects Luna; two genuinely parallel independent equal-capability units may select Luna and Terra; Sol is retained as the final bounded alternate rather than being selected because its identity digest happens to sort first.

`UnitPlan` and `TeamPlan` canonicalize selected and eligible identities against the priority-ordered admitted roster. Scheduling therefore consumes one stable priority sequence, and P2-V0.23.8 candidate-rejection recovery naturally escalates through that same sequence without a separate retry-order authority. P2-V0.23.9 validator-guided alternate-candidate repair remains unchanged and consumes the same already-admitted alternate sequence. Capability eligibility, concurrency and reassignment bounds, protected proposal validation, independent evaluation, safe canonical mutation, source lineage, Git/deployment authority, worker-loss recovery, and the REVIEW ceiling are unchanged.

The ordinary non-agentic `ModelRouter` retains its existing hosted `Luna -> Terra -> Sol` sequence. Architecture v3.24 changes only agent-team selection semantics that previously allowed deterministic identity-digest ordering to override that intended escalation policy.

## Bounded implementation-candidate recovery

Architecture v3.22 distinguishes a **rejected pre-mutation implementation candidate** from worker/process loss. A hosted implementation agent may return syntactically valid model output that fails the server-owned proposal validator or safe candidate-generation contract. That rejection is observation only: it cannot mutate canonical source, accept lineage, write Git, deploy, transition REVIEW, or borrow worker-loss authority.

When candidate generation fails before canonical mutation, the live agentic control plane may retry only the same work unit through another agent identity already present in the server-owned admitted roster and listed in that work unit's eligible-agent set. Retry order is deterministic and server-owned. Every alternate receives an incremented assignment generation plus fresh operation, request, task and attempt identity. Model text, browser input and repository contents cannot select the alternate.

Candidate recovery is finite. The existing `max_reassignments_per_work_unit` bound caps alternate attempts beyond the original assignment. A successful alternate still traverses the unchanged exact acceptance-coverage, safe source proposal, disposable candidate validation, independent evaluation, routing, competition and canonical mutation boundaries. Validation is never relaxed merely to obtain progress.

If all admitted alternatives are rejected, the run fails closed with bounded `CANDIDATE_GENERATION_EXHAUSTED` diagnostic evidence that explicitly records `worker_process_loss=false` and no canonical mutation/lineage authority. Raw provider/model output, secrets and arbitrary exception text are not durable diagnostics. Actual lease expiry, process loss and worker recovery continue to use the pre-existing durable worker recovery state machine and are not reclassified as candidate rejection.

## Validator-guided alternate-candidate repair

Architecture v3.23 makes bounded candidate recovery informative without weakening validation. When a candidate-generation attempt returns a parsed proposal that the unchanged protected proposal validator rejects, the router may project only the server-owned bounded classification `VALIDATION_EXHAUSTED` across the generation boundary. Raw provider/model output, arbitrary exception text, repository text and browser input are not repair diagnostics.

Only a later candidate already admitted for the same work unit by the existing server-owned eligible-agent roster may receive validator-repair guidance. The guidance is fixed server-owned text and only restates the unchanged safe-patch contract: exact canonical path/digest binding and strict single-file unified-diff form. It cannot alter requirements, select a candidate, relax validation, add files or commands, or grant source, lineage, Git, provider, deployment, credential, network, Engineering Run transition or REVIEW authority.

Provider, rate-limit, transport and unrelated generation failures remain separate and do not receive validator-specific guidance. The existing `max_reassignments_per_work_unit` bound, deterministic alternate order and fresh assignment/operation/request/task/attempt identities remain authoritative; v3.23 introduces no same-model retry loop or hidden unbounded recovery.

A first candidate that passes protected proposal validation follows the existing v3.22 path unchanged. If all already-admitted candidates fail, exhaustion remains fail-closed with bounded server-owned rejection-kind evidence, `worker_process_loss=false`, and no mutation claims. Actual process loss continues through durable worker recovery and is never reclassified as candidate rejection.

## Repository-aware protected validation

Protected BUILD/TEST/VERIFY execution is selected from a finite released profile registry. Repository manifests and source files provide bounded compatibility evidence only; they never become executable command authority.

Profile selection runs against the exact disposable candidate tree before canonical mutation and against exact reconstructed accepted lineage for canonical BUILD/TEST/VERIFY. Selection must produce one deterministic profile identity and digest or fail closed as unsupported/ambiguous. Candidate and accepted-lineage evidence carry the selected profile identity so a run cannot silently switch toolchains after admission.

The initial admitted behavior is deliberately narrow:

- the established Parallax mixed Python/Node repository retains its exact historical protected Python commands;
- generic Python repositories remain fail-closed until a separately governed fixed profile is admitted;
- Node repositories remain fail-closed with `NODE_FIXED_VALIDATION_UNAVAILABLE` unless a separately governed safe fixed Node route can avoid repository-defined script command authority;
- a repository with one admissible root `.sln` or `.csproj` may select the fixed `.NET` profile.

For .NET, the target path is normalized relative source evidence. The released commands are fixed `dotnet` invocations. No MSBuild target, property, package source URL, environment value, README text, model output, or user-provided shell fragment becomes a command argument.

Before accepted-lineage materialization, the caller-supplied stage `ExecutionSpec` must still match the server-owned stage authorization envelope. Repository-aware selection occurs only after exact lineage reconstruction and therefore cannot be used to smuggle caller command authority across that boundary.

## Profile-qualified execution snapshots

Snapshot selection is a separate server-owned decision made only after deterministic validation-profile selection from exact candidate or reconstructed accepted-lineage source.

The released finite mapping is:

- `python-v1` → the established common source-free execution snapshot;
- reserved `node-v1` → the same common snapshot for compatibility only; this mapping does not override the selector's existing `NODE_FIXED_VALIDATION_UNAVAILABLE` result and therefore does not admit generic Node source;
- `dotnet-v1` → a dedicated source-free `.NET` execution snapshot containing the released .NET SDK/toolchain and required operating-system runtime dependencies.

Snapshot identifiers are released infrastructure configuration. User text, model output, repository contents, Project metadata, benchmark identity, provider output, and arbitrary profile strings cannot form environment-variable names or select snapshot identity. Unknown profile identities and malformed snapshot IDs fail closed. Missing `.NET` snapshot configuration fails before sandbox creation and must not fall back to the common snapshot.

Disposable candidate validation and accepted-lineage BUILD/TEST/VERIFY use the same resolver. For one admitted profile/configuration they therefore restore the same exact snapshot and record that snapshot ID beside the same validation-profile ID/digest in bounded evidence. Snapshot identity is infrastructure evidence only; it cannot establish source admission, source lineage, Project identity, stage completion, deployment authority, or REVIEW completion.

Toolchain provisioning is a release/operations action, never an Engineering Run action. A released profile image must be produced from a fixed server-owned recipe with pinned or checksum-verified dependencies, contain no Project/application source and no reusable credentials, prove its intended toolchain, transition to effective deny-all networking before publication, and produce an immutable non-expiring snapshot identity. User Engineering Runs must not install operating-system runtimes or SDKs to repair an unqualified image.

Production publication is fail-closed on execution-image readiness. Build preflight restores every production-enabled snapshot under deny-all networking, verifies exact snapshot identity, verifies established Python offline dependencies and compatibility-only `node --version` on the common image, verifies `dotnet --info` on the dedicated .NET image, and proves the protected source root is empty. The Node executable probe preserves common-image capability only; it does not create Node source admission or executable command authority.

Vercel Sandbox remains the current isolated execution provider for this contract. That infrastructure fact is independent of the Project delivery provider: a `source-only` application can use Vercel Sandbox for protected engineering execution and still have no Vercel application deployment or Preview target.

## Bounded dependency PREPARE boundary

A validation profile may declare a subordinate PREPARE contract when clean source requires dependency resolution before offline validation. PREPARE is not an Engineering Run lifecycle stage and cannot complete BUILD/TEST/VERIFY, accept source lineage, mutate Git/provider state, deploy, approve, or promote.

For the initial .NET profile, Parallax:

1. restores the dedicated profile-qualified `.NET` execution snapshot and transfers the exact candidate or accepted-lineage source;
2. probes the server-owned `dotnet` executable using fixed arguments;
3. permits outbound traffic only to the profile-owned NuGet allowlist (`api.nuget.org` and `globalcdn.nuget.org`), with an empty application environment and no Git/provider/deployment credentials;
4. runs fixed `dotnet restore <admitted-target> --nologo`;
5. attempts to replace the sandbox network policy with `deny-all` whether restore succeeds or fails;
6. requires returned runtime state to prove `deny-all` before any BUILD/TEST/VERIFY command can execute;
7. runs fixed offline BUILD/TEST/VERIFY commands with `--no-restore` and no application environment.

A missing toolchain, failed dependency restore, or inability to prove the deny-all transition is a bounded typed non-success (`EXECUTION_PROFILE_UNAVAILABLE`, `DEPENDENCY_PREPARATION_FAILED`, or `VALIDATION_NETWORK_LOCK_FAILED`). These conditions never trigger fallback to another ecosystem, another profile snapshot, arbitrary command execution, broader network access, lineage acceptance, provider mutation, or fabricated progress.

PREPARE may evaluate repository build metadata as part of the package manager/toolchain's normal restore behavior. That untrusted behavior remains confined to the disposable, no-secret sandbox and therefore does not become Parallax command, credential, lineage, deployment, or approval authority.

Vercel Sandbox remains the current isolated execution provider for this contract. That infrastructure fact is independent of the Project delivery provider: a `source-only` application can use Vercel Sandbox for protected engineering execution and still have no Vercel application deployment or Preview target.

## Relationship to W8-S2

W8-S2's deferred Vercel Project-readiness architecture remains authoritative. The original W8-S2 defect was that PLAN incorrectly depended on static Vercel Preview-target registration. v3.16 then exposed and classified a separate credentialed repository-coverage prerequisite.

Architecture v3.17 removed that credential prerequisite for repositories GitHub could prove public, while preserving it for private/inaccessible repositories. Architecture v3.18 removed the repository-specific protected-validation assumption exposed by authenticated OT Time replay. Architecture v3.19 removed the production dependency on GitHub's shared anonymous REST quota for public source bootstrap and prevented public-source throttling from re-entering the Vercel credential path. Architecture v3.20 addresses the next independently exposed boundary: an admitted `.NET` profile may not rely on a Python-qualified common execution image. Architecture v3.21 addresses the next greenfield boundary: a positively empty canonical repository has no commit-bearing source root and must remain mutation-free until verified REVIEW delivery. The required production acceptance remains an authenticated canonical OT Time source-only replay through REVIEW and exact-lineage handoff, while retaining ordinary tenant, spec, run, profile, snapshot, network, and lineage authority.

## Prior production verification

The v3.16 credentialed-repository boundary remains deployment-verified by production API source `0cfe499ac787a23142067e95e80af80dedab36c5`, deployment `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`, and authenticated QA evidence that a non-covered credentialed repository was classified `REPOSITORY_AUTHORIZATION_REQUIRED` before source mutation.

The v3.19 public-source transport change and its Python source-only full-experience proof are recorded in `CURRENT-STATE.md`. Architecture v3.20 does not itself assert deployment verification. Exact v3.20 release/deployment and authenticated OT Time REVIEW/ZIP replay evidence belongs in `CURRENT-STATE.md` only after those steps succeed.


## Human-authorized PLAN refresh after failed IMPLEMENT

A Project-bound Engineering Run using the live agentic runtime may accumulate historical protected PLAN evidence that no longer matches current server-owned orchestration, admitted-agent ordering, routing policy, or competition policy. Such drift must continue to fail closed; historical PLAN evidence is never silently reinterpreted as current.

When an authenticated operator explicitly resumes a run that entered the request in durable `FAILED` state with protected `resume_stage=IMPLEMENT`, the server may select the bounded `PLAN` refresh resume target. This selection is derived only from immutable pre-resume run state, canonical Project binding, and the server-owned agentic-runtime enablement flag. The public resume schema exposes no PLAN-refresh switch, and model/browser/repository text has no authority over the decision.

The resume records a new `RESUMED` control attempt targeting `PLAN` with bounded evidence that the plan refresh was human-authorized. The already-approved terminal-worker preparation remains separate: the old terminal worker becomes `RECOVERING` but receives no lease during PLAN. Autonomous continuation then executes the ordinary protected PLAN runtime against current accepted source lineage and policy. Only after that PLAN succeeds and the run re-enters IMPLEMENT may the existing `RECOVERING -> REASSIGNED` worker transition mint a fresh lease generation for hosted implementation dispatch.

PAUSED resumes and FAILED retries from BUILD, TEST, VERIFY, PLAN, or SPECIFY retain their existing direct resume-stage semantics. Ordinary autonomous calls, reconnects, refreshes, and background execution cannot refresh PLAN or restart a terminal run. Historical attempts, events, worker checkpoints, source lineage, repository/provider authority, production deployment authority, and the explicit REVIEW boundary remain unchanged.
