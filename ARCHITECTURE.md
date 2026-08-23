# Parallax 2.0 Architecture

Version: 2.5
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by PostgreSQL, private immutable object storage, bounded provider adapters and isolated execution infrastructure. Conversation remains the primary product surface. Reason, Code, Work Specifications, Project identity, execution, source lineage, tool authority, protected evaluation, authentication and release evidence remain separate governed capabilities behind that surface.

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
  ├─ protected IMPLEMENT runtime + safe patch engine
  ├─ durable Project/run source-lineage composition
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
          │               ├─ authorized users
          │               ├─ projects
          │               └─ source lineage manifests + transactional heads
          │
          └────────────► bounded provider plane
                          ├─ Vercel Connect → short-lived GitHub App credential
                          ├─ GitHub branch/commit/PR publication
                          └─ project-scoped Vercel Preview deployment
```

Wave 2 closes the first protected app-builder execution loop in production. Preview publication remains the autonomous provider ceiling; production merge/promotion remains outside ordinary autonomous Project execution.

## Core trust boundaries

### Client

The client owns presentation and interaction state. It does not own provider credentials, the production root credential, durable Project truth, durable authorization truth, Work Specification approval authority, accepted source lineage, executable command definitions, tool capabilities, protected evaluation rules or deployment authority.

Assistant text remains ordinary selectable React Native text. React Native Skia is decorative/optical only and reduced-graphics mode preserves equivalent product capability.

Hosted web protected traffic uses same-origin `/p2-api/*` routing to the API. Provider credentials, Vercel execution credentials and the root access secret are never shipped in the browser bundle.

### API

Routes call services/coordinators; services call repositories, execution adapters, lineage gateways and bounded capability registries. Provider SDK details do not leak into public route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` proves the persistence boundary can answer a database query.

Project, conversation, Work Specification, Engineering Run, Reason, Code, access-management, session and bounded-autonomy surfaces remain behind the private authentication boundary.

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

The deployed Wave 2 path is:

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
Project-scoped provider authorization
      ↓
GitHub branch / commit / PR + Vercel Preview
      ↓
Protected app-builder evaluation from persisted evidence
      ↓
Operator REVIEW
```

No fresh-repository fallback is permitted after an accepted IMPLEMENT lineage exists. Later stages must reconstruct and execute the exact accepted lineage.

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

GitHub credentials are short-lived Vercel Connect credentials obtained from Vercel-provided OIDC. Before use, GitHub must prove the minted credential can access the exact canonical repository; mismatched repository reach fails closed.

Vercel Preview credentials are scoped per registered target project. Request-scoped provider composition receives only the selected target/credential, preventing one Project from inheriting another Project's provider authority.

Publication is replay-aware and durable: request/process recreation resolves the accepted delivery record and does not duplicate branch/commit/PR/Preview mutation when the same exact action was already accepted.

Preview remains the autonomous deployment ceiling. Production promotion/merge is an operator/release boundary unless future governance explicitly changes it.

## App-builder evaluation and observability

The protected app-builder evaluator consumes evidence derived from persisted Project, Work Specification, Engineering Run, source-lineage, BUILD/TEST/VERIFY, provider action and provider-audit facts. It does not synthesize success and does not rerun provider mutations simply to evaluate them.

Evidence is bound to canonical Project ID, approved specification revision/digest, run ID, accepted source lineage/content digest, tool capability/request/result/audit identities, published source revision/PR and Preview identity/status where applicable.

Secret-bearing evidence, raw provider responses, credentials, headers/cookies/environment, hidden reasoning/scratchpad and unbounded logs are forbidden.

Scoring remains deterministic with critical-failure semantics. Wrong Project/spec/digest/lineage/stage/provider/Preview/evidence identity, forbidden production authority, denial/failure misrepresentation and unrelated/fresh source fail closed.

The protected reference-app proof recreates request/runtime composition between meaningful stages and proves durable reconstruction, no duplicate implementation mutation, no duplicate publication and correct retry/replay behavior.

## Persistence

SQLAlchemy 2 supports SQLite development and PostgreSQL hosted environments through `DATABASE_URL`. Production uses the dedicated Parallax Supabase PostgreSQL project. Schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Hosted durable schema includes:

- conversations;
- messages;
- work specifications;
- engineering runs;
- engineering attempts;
- authorized users;
- projects;
- source lineage manifests;
- source lineage heads.

Project foreign keys bind conversations and Engineering Runs where required. Source-lineage tables use RLS as defense in depth and revoke direct `anon` / `authenticated` table privileges.

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

`main` is the production source branch. Feature/integration branches create previews. Path-aware ignore behavior may suppress redundant builds when a commit does not affect a project root.

The Vercel Sandbox execution plane, private Blob store and Vercel Connect connectors are runtime infrastructure, not additional long-lived Parallax application deployments.

Release promotion requires exact-head CI, relevant preview evidence, migration readiness, production prerequisite verification, exact production deployment SHA, health/readiness/auth-boundary checks, runtime-error inspection and evidence-based state recording. A green Preview is not production deployment evidence.

## Parallel development and Control Tower

Parallel development is governed by `PROJECT-CONSTITUTION.md`, `PARALLEL-DEVELOPMENT.md` and GitHub as operational authority for active workstreams, branches, PRs, CI/evaluation evidence and integration state.

Workers develop concurrently on isolated branches. Interacting candidates are integrated serially at authoritative boundaries and cumulative protected gates are rerun after material composition changes.

The deployed Wave 2 runtime proves process/request recreation within one app-builder run; Wave 3 extends this into generalized durable worker lease/checkpoint/recovery orchestration.

## Failure degradation

- identity provider unavailable, unauthorized or revoked: fail closed;
- invalid browser session: return to identity gate without retaining provider/root credentials;
- no approved Work Specification: block Code activation;
- Project lookup outside authenticated owner scope: fail as not found;
- Project/spec/run/source-lineage mismatch: block protected progress;
- durable lineage unavailable or compare-and-swap stale: accept no mutation;
- invalid source patch or workspace escape: mutate nothing and return bounded failure evidence;
- Sandbox unavailable/failure/timeout: persist failure evidence and do not advance as success;
- capability unknown/disabled/mismatched/unapproved: deny before provider action;
- provider target/credential/repository mismatch: fail before mutation;
- provider failure: return `FAILED`, never `SUCCEEDED`;
- replay of an already accepted exact provider action: resolve durable delivery rather than duplicate mutation;
- protected evaluation regression: block promotion;
- database readiness failure: block deployment verification;
- unsupported destructive or production authority: return control to the operator.

## Security invariants

No provider secret, production root secret or Vercel execution credential is shipped to the client or sandbox process.

User/model content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, filesystem root, accepted source lineage, tool capabilities, executable commands, registered provider targets, protected evaluation or deployment state.

Major trust boundaries are:

1. authenticated principal and server-owned authorization;
2. canonical Project identity and owner-scoped persistence;
3. approved Work Specification digest/acceptance map;
4. durable Project/run source lineage and single accepted head;
5. confined safe IMPLEMENT mutation;
6. exact-lineage Sandbox execution;
7. server-owned tool capability registry;
8. server-owned provider target/credential registry;
9. persisted provider action/audit and replay identity;
10. protected evaluation/promotion policy;
11. operator authority over production/destructive boundaries.

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

The platform baseline owns non-weakenable guarantees for canonical Project/run identity, specification binding, source lineage, mutation/tool authority, evidence integrity, protected promotion, rollback and human-control boundaries. Project profiles and Work Specifications may strengthen or narrow requirements but cannot silently weaken the baseline.

Wave 3 implements the remaining generalized policy-resolution, worker recovery and end-to-end autonomous validation behavior as protected server-owned runtime capability.

## Approved Wave 3 architecture

Wave 3 extends the deployed Wave 2 loop through:

`approved objective/spec -> PLAN -> typed proposal -> protected mutation -> same-lineage BUILD/TEST/VERIFY -> browser exercise -> deterministic DOM/accessibility/console/network checks -> screenshot regression -> multimodal visual review -> bounded correction/retry -> Git/Preview -> protected evaluation -> operator review`

Deterministic failures are authoritative over visual judgment. The controller preserves last-known-good state and enforces retry, churn, runtime, resource, no-progress and oscillation bounds.

Worker states include `RUNNING`, `PROGRESSING`, `CHECKPOINTED`, `STALLED`, `RECOVERING`, `REASSIGNED`, `HUMAN_REQUIRED`, `READY_FOR_INTEGRATION` and terminal success/failure. Bounded leases, meaningful-progress heartbeats, durable checkpoints and single-writer recovery must permit process loss/reassignment without duplicate mutation or corrupted lineage.

The same architecture governs Parallax self-development and every Project Parallax develops.

### Development optimization mechanisms

Wave 3 adds, subordinate to protected correctness:

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
