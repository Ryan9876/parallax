# Parallax 2.0 Architecture

Version: 2.7
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by PostgreSQL, private immutable object storage, bounded provider adapters and isolated execution infrastructure. Conversation remains the primary product surface. Reason, Code, Work Specifications, Project identity, execution, source lineage, worker recovery, deterministic/browser/visual validation, autonomous correction, tool authority, protected evaluation, authentication and release evidence remain separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ conversation + response state
  ├─ Project select/create
  ├─ Work Specification controls
  ├─ Code / Engineering Run status
  ├─ bounded-autonomy controls
  ├─ Google PKCE sign-in + owner access panel
  ├─ same-origin /p2-api web gateway
  └─ SSE + JSON API client
          │
          ▼
FastAPI intelligence service
  ├─ Google identity verification + authorized-user allowlist
  ├─ signed browser-session boundary + bearer break-glass compatibility
  ├─ Project lifecycle and owner-scoped repository binding
  ├─ conversation + Work Specification persistence
  ├─ Engineering Run kernel + bounded autonomy coordinator
  ├─ durable worker execution / lease / checkpoint / recovery
  ├─ protected IMPLEMENT runtime + safe patch engine
  ├─ durable Project/run source-lineage composition
  ├─ protected deterministic browser / screenshot / visual validation
  ├─ bounded autonomous correction / convergence controller
  ├─ critical-path / impact / reuse / preflight / telemetry controller
  ├─ project-scoped tool-authority registry
  ├─ bounded GitHub + Vercel Preview source delivery
  ├─ Reason / Work Specification / DSPy programs
  ├─ protected command registry
  └─ protected evaluation + observable execution/provider evidence
          │
          ├────────────► Vercel Sandbox execution plane
          │               ├─ exact accepted source lineage
          │               ├─ ephemeral isolated workspace
          │               ├─ registered commands only
          │               ├─ deny-all network policy
          │               ├─ empty application-secret environment
          │               └─ bounded BUILD / TEST / VERIFY evidence
          │
          ├────────────► Vercel private Blob
          │               └─ immutable content-addressed source objects
          │
          ├────────────► hosted PostgreSQL / Supabase
          │               ├─ conversations/messages
          │               ├─ work specifications
          │               ├─ engineering runs/attempts
          │               ├─ engineering worker executions
          │               ├─ authorized users
          │               ├─ projects
          │               └─ source lineage manifests + transactional heads
          │
          └────────────► bounded provider plane
                          ├─ Vercel Connect → short-lived GitHub App credential
                          ├─ GitHub branch/commit/PR publication
                          └─ project-scoped Vercel Preview deployment
```

Wave 3 extends the protected production app-builder loop with durable worker recovery, deterministic browser/visual validation, bounded autonomous correction/convergence and subordinate optimization controls. Preview publication remains the autonomous provider ceiling; production merge/promotion remains outside ordinary autonomous Project execution.

## Core trust boundaries

### Client

The client owns presentation and interaction state. It does not own provider credentials, the production root credential, durable Project truth, durable authorization truth, Work Specification approval authority, accepted source lineage, worker leases/checkpoints, executable command definitions, tool capabilities, protected validation/evaluation rules or deployment authority.

Assistant text remains ordinary selectable React Native text. React Native Skia is decorative/optical only and reduced-graphics mode preserves equivalent product capability.

Hosted web protected traffic uses same-origin `/p2-api/*` routing to the API. Provider credentials, Vercel execution credentials and the root access secret are never shipped in the browser bundle.

### API

Routes call services/coordinators; services call repositories, execution adapters, lineage gateways, worker-recovery services, validation/correction controllers and bounded capability registries. Provider SDK details do not leak into public route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` proves the persistence boundary can answer a database query.

Project, conversation, Work Specification, Engineering Run, worker state, Reason, Code, access-management, session and bounded-autonomy surfaces remain behind the private authentication boundary.

### External provider plane

Provider authority is resolved only after canonical authenticated Project resolution. Repository identity, connector identity, Preview target identity and credentials are server-owned registrations. Models and clients cannot provide arbitrary provider endpoints, tokens, repositories or deployment projects.

## Identity and access architecture

Google/Supabase proves interactive identity. Parallax decides application authorization through the server-owned `authorized_users` allowlist.

Each protected request resolves an `AccessPrincipal`. Project ownership is derived from that authenticated principal; caller-supplied owner identity is never trusted as authorization input.

RLS remains enabled on server-owned hosted tables and direct `anon` / `authenticated` table privileges are revoked where the server-mediated boundary is required. FastAPI remains the application authorization layer.

`PARALLAX_ACCESS_TOKEN` is a server-only break-glass/automation credential. It is not the normal browser login path and is not forwarded into sandboxes or provider calls.

## Canonical Project identity

`Project.id` is the canonical durable application identity. A Project also carries authenticated owner identity, owner-local metadata, optional bounded `repository_ref`, opaque `workspace_ref = project:<id>`, lifecycle/status metadata and timestamps.

`workspace_ref` is identity, not a filesystem path or execution authority. `repository_ref` is repository identity, not Git/network/deployment authority.

Conversation and Engineering Run Project binding use the canonical Project ID. Existing historical rows may remain unbound where migration policy intentionally preserved prior state; new protected Code execution requires canonical Project binding.

No client, model, provider or execution adapter may create a competing durable Project identity for an already resolved Project.

## Work Specification and execution binding

A Work Specification is the operator-controlled implementation contract for one bounded objective. AI may draft it; only an explicit protected operator mutation approves it.

Every authoritative Code Engineering Run is bound to one approved Work Specification revision/digest. Stable acceptance IDs are server-derived in list order (`AC-01`, `AC-02`, ...). Clients, models and tools may provide evidence against those IDs but cannot redefine the required set.

Protected lifecycle:

`SPECIFY -> PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW -> COMPLETE`

Protected validators require exact acceptance coverage and observable evidence. Missing, duplicated, extra or client-defined acceptance identities fail closed.

## Protected app-builder runtime

The deployed Wave 3 path is:

```text
Authenticated principal
      ↓
Canonical Project.id + server-owned repository target
      ↓
Approved Work Specification revision/digest
      ↓
Engineering Run / PLAN
      ↓
Repository bootstrap or durable current source lineage
      ↓
Typed IMPLEMENT proposal
      ↓
Safe source mutation in a disposable materialization
      ↓
Transactional acceptance of immutable source lineage
      ↓
BUILD / TEST / VERIFY on that exact accepted lineage
      ↓
Deterministic browser / accessibility / console / network / layout validation
      ↓
Screenshot regression
      ↓
Bounded secondary multimodal visual review
      ↓
Bounded correction / fresh exact-lineage revalidation / LKG convergence
      ↓
Project-scoped provider authorization
      ↓
GitHub branch / commit / PR + Vercel Preview
      ↓
Protected app-builder evaluation from persisted evidence
      ↓
Operator REVIEW
```

No fresh-repository fallback is permitted after an accepted IMPLEMENT lineage exists. Later stages and corrected candidates must reconstruct and validate the exact accepted lineage.

## Safe IMPLEMENT mutation

The safe patch engine accepts only an explicit isolated filesystem root plus bounded patch requests. Requests bind to a relative path, expected base digest, supported unified diff and bounded source/patch/result sizes.

It fails closed on traversal, symlink escape, binary/unsupported targets, secret-sensitive paths, malformed headers, stale base digests, unsupported rename/delete/chmod/directory semantics, duplicate targets, no-op patches and size violations.

Multi-file implementation prepares all mutations before commit and rolls back on commit failure. Successful mutation evidence contains deterministic before/after/diff/artifact identity, never authority to bypass protected stage validation.

## Durable source lineage

Authoritative source continuity is content-addressed and split across two durable systems:

- immutable source objects live in private Vercel Blob;
- bounded lineage manifests and the transactional current Project/run head live in PostgreSQL.

`source_lineage_manifests` records immutable manifest identity and parentage. `source_lineage_heads` provides the Project/run current-head compare-and-swap boundary. Source bytes are intentionally absent from PostgreSQL.

Local filesystem roots are disposable materializations only. They may be reconstructed from durable lineage after request/process recreation and must never be represented as authoritative persistence.

Accepted IMPLEMENT performs exact parent-lineage validation, verifies mutation artifacts against workspace bytes, advances lineage transactionally and cleans the disposable lease. Duplicate/stale acceptance fails closed.

## Exact-lineage BUILD / TEST / VERIFY

BUILD, TEST and VERIFY execute registered commands in isolated Vercel Sandboxes over a reconstruction of the accepted source lineage. Sandboxes are short-lived, deny network by default, receive no application-secret environment and are destroyed after use.

Only bounded observable evidence is retained: stage identity, source-lineage identity, command identity, invocation digest, exit state, duration, bounded output excerpts/digests, timeout/redaction/network-policy identity and acceptance coverage.

A stage result from another Project, run, Work Specification or source lineage cannot satisfy the protected run.

## Durable worker execution and recovery

`engineering_worker_executions` is the production server-owned control record for live autonomous worker ownership and recovery. It permits one durable worker execution per Engineering Run and is not a second Engineering Run/source-lineage state machine.

A worker lease binds an opaque owner identity, monotonically increasing generation and bounded expiry. Only the current live generation has checkpoint/mutation authority. After reassignment, an abandoned/stale lease fails closed.

Canonical checkpoints bind the same protected Project/run/Work Specification identity to current bounded step, accepted source lineage, last-known-good lineage, evidence/dependency references and retry/progress state. Worker-local memory is never authoritative.

Recoverable process loss follows protected transitions such as:

`RUNNING / PROGRESSING -> CHECKPOINTED -> STALLED -> RECOVERING -> REASSIGNED -> PROGRESSING`

Reassignment preserves the durable execution identity and increments the lease generation. Ordinary process loss is recovered from the durable checkpoint without requiring a manual Engineering Run `resume`; `HUMAN_REQUIRED` is reserved for genuine specification, authority, credential or other protected human boundaries.

Retry, no-progress and oscillation counters are bounded. Meaningful-progress state, not status chatter/token activity, drives recovery decisions.

## Browser, visual validation and autonomous correction

Protected browser validation runs deterministic semantics before visual judgment. DOM/functional behavior, accessibility, console, network and layout failures are authoritative. A screenshot comparator or multimodal reviewer cannot convert a deterministic failure into success.

Screenshot evidence is provenance-bound to the exact Project/run/source-lineage/Preview target. Multimodal review is bounded, secondary evidence after deterministic checks pass.

Correctable defects are normalized into bounded evidence and fed to the autonomous correction controller. Every correction creates or consumes an immutable candidate lineage and must pass fresh protected validation on that exact lineage before it can advance.

The controller preserves a last-known-good candidate. Regressive or equal-quality changes do not replace it. Repeated same-defect, no-progress, oscillating A/B/A, churn, compute and elapsed-runtime limits stop the loop at explicit bounded conditions rather than consuming unbounded work.

## Development optimization controller

The deployed optimization controller is subordinate to correctness and authority. It can prioritize the dependency critical path, apply integration backpressure, propose graph/lease/path-safe work stealing, select proven change-impact validation, reuse provenance-safe caches/patterns/repair memory, route within approved model classes, preflight specifications, create disposable speculative integration candidates, preserve acceptance ownership during workstream sizing and record bounded development-performance telemetry.

Optimization outputs cannot advance accepted source lineage, waive worker/integration/release full gates, widen Project/tool/provider authority, promote speculative results or cross Project-private evidence boundaries. Unknown or unproven impact falls back to full validation.

## Project-scoped tool authority

The tool layer defines immutable typed capabilities, authority requests, approvals, decisions, results and audit records. A server-owned registry is authoritative. Model/user input cannot create or widen capabilities.

Authorization requires exact registered Project/tool/action matching. Destructive actions require explicit approval by invariant. Generic shell, arbitrary command, raw HTTP, arbitrary URL/header/environment and unregistered network escape hatches are rejected.

Results distinguish `DENIED`, `FAILED` and `SUCCEEDED`; provider failure or authority denial can never be represented as success.

## Bounded GitHub and Vercel Preview delivery

Production source delivery is selected from a server-owned target registry after owner-scoped canonical `Project.repository_ref` resolution.

Each registered target binds:

- exact repository identity and GitHub repository ID;
- production branch identity;
- Vercel Preview project/team identity;
- one GitHub Vercel Connect connector reference;
- one Vercel credential environment-variable reference.

The current Parallax self-target uses `github/parallax-runtime` and `vercel:preview:parallax`.

GitHub credentials are short-lived Vercel Connect credentials obtained from Vercel-provided OIDC. A slash-bearing connector identity is serialized as one percent-encoded URL path parameter at the Connect wire boundary; decoded URL representations are not accepted as sufficient contract evidence. Before use, GitHub must prove the minted credential can access the exact canonical repository; mismatched repository reach fails closed.

Vercel Preview credentials are scoped per registered target project. Request-scoped provider composition receives only the selected target/credential, preventing one Project from inheriting another Project's provider authority.

Publication is replay-aware and durable: request/process recreation resolves the accepted delivery record and does not duplicate branch/commit/PR/Preview mutation when the same exact action was already accepted.

The Parallax self-development API release path additionally performs a production-only, read-only provider preflight before a new production deployment may become READY. Using the deployment's Vercel OIDC identity and the same server-owned target registry, the preflight verifies the encoded Vercel Connect exchange, exactly one GitHub installation repository, matching repository numeric identity, registered production branch resolution and presence of the target-scoped Vercel Preview credential. Preview deployments intentionally skip this provider call because the Connect connector remains production-only; the gate does not broaden Preview authority.

Preview remains the autonomous deployment ceiling for Parallax-developed Projects. Parallax's own production promotion/merge remains a governed release boundary. While the standing single-user authority in `PROJECT-CONSTITUTION.md` is active, that durable authorization can satisfy the per-release human-approval step only after all required exact-head gates and rollback requirements pass; it does not give the Project runtime autonomous production-deployment authority.

## App-builder evaluation and observability

The protected app-builder evaluator consumes evidence derived from persisted Project, Work Specification, Engineering Run, source-lineage, BUILD/TEST/VERIFY, provider action and provider-audit facts. It does not synthesize success and does not rerun provider mutations simply to evaluate them.

Evidence is bound to canonical Project ID, approved specification revision/digest, run ID, accepted source lineage/content digest, tool capability/request/result/audit identities, published source revision/PR and Preview identity/status where applicable.

Secret-bearing evidence, raw provider responses, credentials, headers/cookies/environment, hidden reasoning/scratchpad and unbounded logs are forbidden.

Scoring remains deterministic with critical-failure semantics. Wrong Project/spec/digest/lineage/stage/provider/Preview/evidence identity, forbidden production authority, denial/failure misrepresentation and unrelated/fresh source fail closed.

The permanent Wave 3 protected reference-app proof recreates process/runtime composition between meaningful stages and proves durable worker reassignment, stale-worker rejection, exact lineage/LKG reconstruction, no duplicate implementation mutation, no duplicate publication, browser/visual precedence, bounded correction/convergence and correct retry/replay behavior.

## Persistence

SQLAlchemy 2 supports SQLite development and PostgreSQL hosted environments through `DATABASE_URL`. Production uses the dedicated Parallax Supabase PostgreSQL project. Schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Hosted durable schema includes:

- conversations;
- messages;
- work specifications;
- engineering runs;
- engineering attempts;
- engineering worker executions;
- authorized users;
- projects;
- source lineage manifests;
- source lineage heads.

Project foreign keys bind conversations and Engineering Runs where required. Source-lineage and worker-execution tables use RLS as defense in depth and revoke direct `anon` / `authenticated` table privileges. Server-owned control-plane tables intentionally require no direct-client policy; FastAPI remains the application authorization boundary.

## Reason and model routing

Reason remains provider-independent and bounded by durable context. Later explicit user corrections supersede conflicting earlier assistant assumptions.

Scope routing proposes `CONTINUE`, `CLARIFY` or `SPEC_AMENDMENT`; protected server policy owns the transition. Invalid, secret-bearing, hidden-reasoning or scope-incompatible candidates are rejected/escalated rather than exposed.

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

DSPy operates in development specification compilation. Promotion validates the committed compiled plan and protected acceptance map deterministically; stochastic regeneration is not itself a promotion oracle.

## Deployment topology

Two authoritative Vercel projects deploy from the same repository:

1. Web `parallax` — root `apps/client`, Expo static export.
2. API `parallax-api` — root `services/api`, FastAPI via `api/index.py`.

`main` is the production source branch. Feature/integration branches create previews. Path-aware ignore behavior may suppress redundant builds when a commit does not affect a project root. An API-only production release may therefore deploy a new API SHA while intentionally preserving the existing verified client artifact.

The Vercel Sandbox execution plane, private Blob store and Vercel Connect connectors are runtime infrastructure, not additional long-lived Parallax application deployments.

Release promotion requires exact-head CI, relevant preview evidence, migration readiness, production prerequisite verification, exact production deployment SHA, health/readiness/auth-boundary checks, runtime-error inspection and evidence-based state recording. For the Parallax API, a production build must also pass the read-only provider preflight before Vercel cutover. A green Preview is not production deployment evidence, and the production-only provider preflight does not replace post-deploy smoke/observability checks.

While Parallax remains effectively single-user, `PROJECT-CONSTITUTION.md` v1.4 provides standing authority to promote an already validated Parallax release/hotfix without another per-release approval request. The authority expires when additional real users begin relying on production and never waives the release gates above.

## Parallel development and Control Tower

Parallel development is governed by `PROJECT-CONSTITUTION.md`, `PARALLEL-DEVELOPMENT.md` and GitHub as operational authority for active workstreams, branches, PRs, CI/evaluation evidence and integration state.

Workers develop concurrently on isolated branches. Interacting candidates are integrated serially at authoritative boundaries and cumulative protected gates are rerun after material composition changes.

The deployed Wave 3 runtime includes generalized durable worker lease/checkpoint/recovery orchestration, deterministic browser/visual validation, bounded autonomous correction and subordinate optimization controls in addition to the Wave 2 app-builder foundations.

## Failure degradation

- identity provider unavailable, unauthorized or revoked: fail closed;
- invalid browser session: return to identity gate without retaining provider/root credentials;
- no approved Work Specification: block Code activation;
- Project lookup outside authenticated owner scope: fail as not found;
- Project/spec/run/source-lineage mismatch: block protected progress;
- durable lineage unavailable or compare-and-swap stale: accept no mutation;
- invalid source patch or workspace escape: mutate nothing and return bounded failure evidence;
- Sandbox unavailable/failure/timeout: persist failure evidence and do not advance as success;
- expired/stale worker lease: reject checkpoint/mutation authority;
- recoverable process loss: classify, stall and resume/reassign from the durable canonical checkpoint within bounds;
- true specification/authority/credential boundary: enter `HUMAN_REQUIRED` rather than disguising it as ordinary retry;
- deterministic browser/accessibility/console/network/layout failure: block pass; visual judgment cannot override it;
- regressive/equal/no-progress/oscillating correction: preserve last-known-good and stop/retry only within protected bounds;
- unknown change impact or incomplete reuse/cache provenance: discard optimization and run the conservative/full path;
- capability unknown/disabled/mismatched/unapproved: deny before provider action;
- provider target/credential/repository mismatch: fail before mutation;
- malformed connector wire identity or production provider preflight failure: fail the candidate production build before cutover;
- provider failure: return `FAILED`, never `SUCCEEDED`;
- replay of an already accepted exact provider action: resolve durable delivery rather than duplicate mutation;
- protected evaluation regression: block promotion;
- database readiness failure: block deployment verification;
- unsupported destructive or production authority outside an active explicit/standing authorization: return control to the operator.

## Security invariants

No provider secret, production root secret or Vercel execution credential is shipped to the client or sandbox process.

User/model content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, filesystem root, accepted source lineage, worker ownership/generation/checkpoint authority, deterministic validation precedence, correction/LKG policy, tool capabilities, executable commands, registered provider targets, protected evaluation or deployment state.

Major trust boundaries are:

1. authenticated principal and server-owned authorization;
2. canonical Project identity and owner-scoped persistence;
3. approved Work Specification digest/acceptance map;
4. durable Project/run source lineage and single accepted head;
5. confined safe IMPLEMENT mutation;
6. exact-lineage Sandbox execution;
7. durable single-writer worker lease/checkpoint/recovery authority;
8. deterministic browser/accessibility/console/network/layout evidence;
9. bounded visual review and correction/LKG/convergence policy;
10. server-owned optimization policy with non-authoritative speculation/reuse;
11. server-owned tool capability registry;
12. server-owned provider target/credential registry and encoded connector wire contract;
13. persisted provider action/audit and replay identity;
14. protected evaluation/promotion policy;
15. governed production release authority plus fail-closed production provider preflight.

## Inherited development-policy architecture

Every Parallax-developed Project inherits one protected policy stack:

```text
Parallax platform baseline
        ↓ may only be preserved or strengthened
Project profile
        ↓ may only be preserved or strengthened
Approved Work Specification
        ↓
Capability-specific validation plan
        ↓
Protected execution / evaluation / promotion
```

The platform baseline owns non-weakenable guarantees for canonical Project/run identity, specification binding, source lineage, worker/mutation/tool authority, evidence integrity, deterministic validation precedence, protected promotion, rollback and human-control boundaries. Project profiles and Work Specifications may strengthen or narrow requirements but cannot silently weaken the baseline.

The deployed Wave 3 runtime implements generalized policy resolution, worker recovery, browser/visual validation, correction/convergence and development optimization as protected server-owned capability.

## Deployed Wave 3 architecture

Wave 3 extends the protected app-builder loop through:

`approved objective/spec -> PLAN -> typed proposal -> protected mutation -> same-lineage BUILD/TEST/VERIFY -> browser exercise -> deterministic DOM/accessibility/console/network/layout checks -> screenshot regression -> bounded multimodal visual review -> bounded correction/retry with LKG -> Git/Preview -> protected evaluation -> operator review`

Deterministic failures are authoritative over visual judgment. The controller preserves last-known-good state and enforces retry, churn, runtime, resource, no-progress and oscillation bounds.

Worker states include `RUNNING`, `PROGRESSING`, `CHECKPOINTED`, `STALLED`, `RECOVERING`, `REASSIGNED`, `HUMAN_REQUIRED`, `READY_FOR_INTEGRATION` and terminal success/failure. Bounded leases, meaningful-progress checkpoints and single-writer recovery permit process loss/reassignment without duplicate mutation or corrupted lineage.

The same architecture governs Parallax self-development and every Project Parallax develops.

### Development optimization mechanisms

Wave 3 deploys, subordinate to protected correctness:

1. critical-path scheduling and bounded work stealing;
2. change-impact-driven validation while retaining full promotion suites;
3. immutable secret-free warm environments;
4. validated pattern/component/config reuse;
5. privacy-safe failure fingerprinting and repair memory;
6. adaptive model routing without lower promotion thresholds;
7. specification preflight;
8. disposable speculative integration;
9. automatic workstream sizing/rebalancing;
10. development-performance telemetry.

Additional controller mechanisms include value-of-information scheduling, safe-boundary cancellation/supersession and integration-capacity backpressure. The server-side DAG/policy/controller is authoritative; models may suggest but do not own scheduling or authority.

Optimization targets validated outcome time, not worker utilization or token throughput. Identity, provenance, single-writer, privacy, evaluation and human-control guarantees may not be approximated for speed.