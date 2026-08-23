# Parallax 2.0 Architecture

Version: 2.3
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by durable PostgreSQL persistence in hosted environments. Conversation remains the primary product surface. Reason, Code, Work Specifications, Project identity, execution, tool authority, protected evaluation, authentication and release evidence remain separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ conversation + response state
  ├─ Work Specification controls
  ├─ Code / Engineering Run status
  ├─ bounded-autonomy control
  ├─ Google PKCE sign-in + owner access panel
  ├─ same-origin /p2-api web gateway
  └─ SSE + JSON API client
          │
          ▼
FastAPI intelligence service
  ├─ Google identity verification + authorized-user allowlist
  ├─ signed browser-session boundary + bearer break-glass compatibility
  ├─ Project lifecycle service
  ├─ conversation + Work Specification persistence
  ├─ Engineering Run kernel
  ├─ bounded autonomy coordinator
  ├─ safe source implementation / patch engine
  ├─ project-scoped tool-authority contracts + registry
  ├─ Reason / Work Specification / DSPy programs
  ├─ protected command registry
  ├─ protected evaluation + app-builder evaluation spine
  └─ observable execution/failure evidence
          │
          ├────────────► Vercel Sandbox execution plane
          │               ├─ ephemeral isolated workspace
          │               ├─ registered commands only
          │               ├─ deny-all network policy
          │               ├─ empty application-secret environment
          │               └─ bounded observable evidence
          │
          └────────────► hosted PostgreSQL / Supabase
                          ├─ conversations/messages
                          ├─ work specifications
                          ├─ engineering runs/attempts
                          ├─ authorized users
                          └─ projects
```

Wave 1 establishes the Project, safe source mutation, tool-authority and app-builder evaluation foundations. It does **not** yet complete the full project-scoped app-building runtime. The missing integration is explicit in later sections.

## Core trust boundaries

### Client

The client owns presentation and interaction state. It does not own provider credentials, the production root credential, durable Project truth, durable authorization truth, Work Specification approval authority, required acceptance criteria, executable command definitions, tool capabilities, protected evaluation rules or deployment authority.

Assistant text remains ordinary selectable React Native text. React Native Skia is decorative/optical only and the reduced-graphics path preserves equivalent product capability.

The response reducer owns visible response state. Product state drives animation; animation state cannot redefine application authority.

Hosted web protected traffic uses same-origin `/p2-api/*` routing to the API. Provider credentials, Vercel execution credentials and the root access secret are never shipped in the browser bundle.

### API

Routes call services/coordinators; services call repositories, intelligence modules, execution adapters and bounded capability registries. Provider SDK details do not leak into route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` proves the persistence boundary can answer a database query.

Project, conversation, Work Specification, Engineering Run, Reason, Code, access-management, session and bounded-autonomy surfaces remain behind the private authentication boundary.

## Identity and access architecture

Google/Supabase proves interactive identity. Parallax decides application authorization through the server-owned `authorized_users` allowlist.

Each protected request resolves an `AccessPrincipal`. Project ownership is derived from that authenticated principal; caller-supplied owner identity is never trusted as authorization input.

RLS remains enabled on server-owned hosted tables and direct `anon` / `authenticated` table privileges are revoked where the server-mediated boundary is required. FastAPI remains the application authorization layer.

`PARALLAX_ACCESS_TOKEN` is a server-only break-glass/automation credential. It is not the normal browser login path and is not forwarded into the bounded sandbox.

## Canonical Project/App identity

Wave 1 introduces a durable first-class Project boundary.

A Project has:

- server-generated UUID `Project.id` — the canonical durable application identity;
- authenticated owner subject;
- owner-local slug and display metadata;
- optional bounded `repository_ref` identity metadata;
- immutable opaque `workspace_ref = project:<id>`;
- lifecycle/status metadata and timestamps.

The Project service exposes protected create/list/read operations and owner-scoped repository access. Cross-owner reads are treated as not found rather than leaking record existence.

### Project identity invariants

`Project.id` is the canonical value downstream project-scoped contracts must bind to.

`workspace_ref` is an opaque identity seam. It is **not** a filesystem path, sandbox ID or execution authority. A later protected allocator must map Project identity to an isolated filesystem workspace.

`repository_ref` is bounded repository identity metadata. It is **not** Git authority, network authority, connector authority or deployment permission.

No model, client or tool may create a competing durable Project identity for an already resolved Project.

## Specification identities

Parallax maintains two distinct specification concepts.

### Product-policy specification

`Conversation.spec_id` records the product/policy specification identity under which the conversation was created and governed.

### User Work Specification

A Work Specification is the operator-controlled implementation contract for one objective. It contains a durable revision/lifecycle, objective, constraints, acceptance criteria, risks/open questions, confidence and drafting metadata.

AI may draft; only an explicit protected operator mutation approves. A model cannot approve its own specification.

Wave 1 does not yet add a Project foreign key to existing Work Specifications or Engineering Runs. Project binding is a Wave 2 integration requirement and must use the canonical Project identity rather than a parallel identifier.

## Approved-Spec Code execution binding

Every authoritative Code Engineering Run is bound to one approved Work Specification revision. The server owns the Work Specification digest and derives stable acceptance IDs in list order:

```text
criterion 1 -> AC-01
criterion 2 -> AC-02
criterion 3 -> AC-03
...
```

Clients, models and tools may provide evidence against those IDs but cannot redefine the required set.

Protected lifecycle:

`SPECIFY -> PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW -> COMPLETE`

Protected validators require exact acceptance coverage and real observable evidence. Missing, duplicated, extra or client-defined acceptance IDs fail closed.

## Safe source implementation foundation

Wave 1 adds a standalone safe source mutation primitive for the IMPLEMENT gap.

The implementation engine accepts an explicit isolated filesystem root plus bounded patch requests. Each request binds to:

- a relative target path;
- exact expected base digest for existing files;
- a strict supported unified diff;
- bounded source/patch/result sizes.

### Source-mutation safety invariants

The engine fails closed on:

- path traversal or workspace escape;
- symlink escape;
- binary or unsupported targets;
- secret-sensitive target paths;
- malformed or mismatched diff headers;
- stale base digest or changed pre-image;
- unsupported rename/delete/chmod/directory semantics;
- duplicate targets;
- no-op patches;
- per-file or aggregate size-limit violations.

Multi-file implementation prepares all mutations before commit and rolls back on commit failure. Successful output includes deterministic before/after/diff/artifact evidence and workspace digest material.

`applied: true` means the bounded source mutation succeeded. It does **not** authorize the protected IMPLEMENT stage. The engine explicitly reports `protected_stage_authority: false` and exposes no shell, Git, network or deployment authority.

## Bounded autonomy execution plane

The existing bounded-autonomy coordinator remains the orchestration authority for protected Code progression.

At PLAN it performs execution-provider preflight and may construct deterministic plan evidence from the immutable acceptance map.

Before Wave 1 integration, IMPLEMENT deliberately stopped with `IMPLEMENTATION_REQUIRED`. The new safe patch engine provides the missing mutation primitive, but it is not yet wired into the coordinator because Project-to-workspace allocation and persistent workspace continuity are still required.

BUILD, TEST and VERIFY currently execute registered commands through isolated Vercel Sandboxes and pass evidence through existing protected validators.

### Current workspace continuity limitation

The existing Sandbox stages create fresh isolated repository-backed sandboxes. Wave 1 source mutation operates against an explicit isolated filesystem root. The architecture does not yet guarantee that the exact mutated implementation workspace/revision is the source carried through BUILD -> TEST -> VERIFY.

Wave 2 must introduce one protected project/run workspace lineage so later stages verify the code that IMPLEMENT actually produced.

### Protected command registry

Executable policy remains server-owned code. User/model content cannot supply arbitrary shell strings. Commands are structured executable/argument arrays selected by protected stage policy.

### Vercel Sandbox executor

Production-capable execution runs outside the FastAPI host using Vercel Sandbox. Sandboxes are short-lived, deny network by default, receive no application-secret environment and are destroyed after use.

Only bounded observable evidence is retained: tool identity, invocation digest, exit status, duration, stdout/stderr digests, bounded excerpts, timeout/redaction/network policy identity and protected acceptance coverage as required.

## Project-scoped tool authority

Wave 1 introduces provider-neutral tool authority contracts before concrete provider adapters.

The tool layer defines immutable typed:

- capabilities;
- authority requests;
- human approvals;
- authorization decisions;
- tool results;
- audit records.

A server-owned registry is authoritative. Model/user input cannot create or widen a capability.

### Tool-authority invariants

Authorization requires exact registered project/tool/action matching.

Unknown, disabled or mismatched capability state fails closed.

Destructive actions require human approval by invariant. Approval binds to exact request/capability/project/tool/action identity and cannot be reused to widen authority.

Generic shell/exec/command/subprocess/raw-HTTP/network escape-hatch identities are rejected. Tool contracts intentionally do not expose arbitrary command, URL, request-body, header, environment or generic payload fields.

Results distinguish `DENIED`, `FAILED` and `SUCCEEDED`; provider failure or authority denial can never be represented as success.

Tool/audit `project_ref` must be bound to the canonical `Project.id` after authenticated owner-scoped Project resolution. `workspace_ref` and `repository_ref` are not authority substitutes.

Concrete GitHub/Vercel/database adapters are not part of Wave 1 and must preserve these contracts.

## App-builder evaluation and observability spine

Wave 1 adds a separate protected app-builder benchmark/evidence boundary above runtime implementation details.

Versioned development and promotion suites cover:

- Project isolation/binding;
- specification binding;
- bounded implementation evidence;
- BUILD/TEST/VERIFY truthfulness;
- tool authority;
- interruption/recovery/idempotency behavior;
- evidence hygiene.

Scoring is deterministic and includes critical-failure semantics. Secret-bearing evidence, hidden reasoning/scratchpad fields, malformed requirements, contradictory requirements, forbidden observations and project/workspace/spec mismatches fail closed.

Evaluation outputs retain bounded observable identifiers and digests rather than raw provider payloads. Passing evaluation does not itself grant execution, merge or deployment authority.

### Runtime evidence mapping requirement

Wave 2 must adapt accepted runtime interfaces into this evidence vocabulary:

- Project evidence binds to canonical Project ID and opaque workspace identity;
- implementation evidence binds to source/workspace/artifact digests and explicit negative-authority flags;
- tool evidence binds to capability/request/result/audit identifiers and canonical digests;
- BUILD/TEST/VERIFY evidence must prove it operated on the same accepted implementation lineage.

## Inherited development-policy architecture

Every Parallax-developed Project inherits one protected development-policy stack. This is a platform architecture rule, not a convention copied into individual projects.

Effective policy is composed in strict order:

```text
Parallax platform baseline
        ↓ may only be preserved or strengthened
Project profile
        ↓ may only be preserved or strengthened
Approved Work Specification
        ↓
Runtime capability-specific validation plan
        ↓
Protected execution / evaluation / promotion
```

The **platform baseline** owns non-weakenable guarantees for canonical Project/run identity, specification binding, source lineage, mutation/tool authority, durable checkpoints, bounded autonomy, single-writer execution, stall/recovery behavior, evidence integrity, protected promotion, rollback and human-control boundaries.

The **Project profile** supplies durable project-specific requirements such as repository/build topology, architecture rules, design system, supported platforms, security posture, testing matrix, accessibility level, performance budgets, compatibility constraints, deployment targets and operational requirements. It can make the platform baseline stricter but cannot disable or silently relax it.

The **Work Specification** binds one bounded objective to explicit acceptance criteria and constraints. It may narrow scope or add stricter requirements but cannot widen tool/release authority or weaken platform/Project controls.

The **capability-specific validation plan** adapts testing to what is actually being built without weakening the common policy. For example, web/mobile applications may require browser workflows, responsive/layout checks, accessibility, screenshot regression and multimodal visual review; APIs may require schema/contract, authorization, integration, reliability and performance checks; CLIs may require command/workflow/exit-code/terminal-output checks. Unsupported validation requirements fail closed or require an explicit human-approved exception rather than being silently skipped.

Wave 3 must implement the policy stack as protected server-owned behavior. The current architecture records this as an accepted future runtime contract; it does not claim the deployed Wave 1 runtime already enforces Wave 3 inheritance.

## Reason architecture

Reason remains provider-independent and bounded by durable context. Later explicit user corrections supersede conflicting earlier assistant assumptions.

Scope routing proposes `CONTINUE`, `CLARIFY` or `SPEC_AMENDMENT`; protected server policy owns the transition. Invalid, secret-bearing, hidden-reasoning or scope-incompatible candidates are rejected/escalated rather than exposed.

Reason responses use SSE. The client renders semantic text while optical effects follow response state.

## Persistence

SQLAlchemy 2 supports SQLite development and PostgreSQL hosted environments through `DATABASE_URL`.

Production uses the dedicated Parallax Supabase PostgreSQL project through the server boundary. Schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Hosted durable schema now includes:

- conversations;
- messages;
- work specifications;
- engineering runs;
- engineering attempts;
- authorized users;
- projects.

The Project migration uses owner-local uniqueness, unique opaque workspace identity, RLS and revoked direct client-role access.

Existing Work Specification and Engineering Run rows remain structurally compatible; Project foreign-key binding is intentionally deferred to Wave 2 rather than retrofitted unsafely during the foundation slice.

## Model routing and DSPy

Runtime escalation order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

Scope, Reason and Work Specification drafting use typed boundaries and protected validation.

DSPy also operates in development specification compilation. Workstream promotion validates the exact committed DSPy-generated plan and protected acceptance map deterministically. Stochastic local-model regeneration is not itself a promotion oracle. The repository release lane continues to execute the DSPy compiler path as an independent execution proof.

Optimizer-controlled code cannot alter protected promotion, authorization or execution authority.

## Deployment topology

Two authoritative Vercel projects deploy from the same repository:

1. Web `parallax` — root `apps/client`, Expo static export.
2. API `parallax-api` — root `services/api`, FastAPI via `api/index.py`.

`main` is the production source branch. Feature/integration branches create previews. Path-aware ignore commands suppress redundant builds when a commit does not affect that project's root.

The Vercel Sandbox execution plane is runtime infrastructure, not a third long-lived Parallax application deployment.

Release promotion requires exact-head CI, relevant preview evidence, migration readiness for schema changes, production deployment readiness, health/readiness verification, protected-route behavior verification and evidence-based state recording.

## Parallel development architecture

Parallel ChatGPT development is governed by `PROJECT-CONSTITUTION.md` v1.2 and `PARALLEL-DEVELOPMENT.md`.

GitHub is the operational authority for active workstream ownership, branches, PRs, CI/evaluation evidence and integration state.

Workers develop concurrently on isolated branches, but interacting candidates are integrated serially. The Wave 1 release demonstrated this by merging #43 -> #44 -> #45 -> #46 onto a cumulative integration branch and rerunning the protected gates between interacting additions before promotion to `main`.

## Failure degradation

- Skia unavailable: preserve semantic content/capability in reduced-graphics mode.
- Identity provider unavailable or identity unauthorized/revoked: fail closed.
- Browser session invalid: return to identity gate without retaining provider/root credentials.
- No approved Work Specification: block Code activation.
- Project lookup outside authenticated owner scope: fail as not found.
- Project/workspace/spec binding mismatch: block protected progress.
- Invalid source patch or workspace escape attempt: mutate nothing and return bounded failure evidence.
- Bounded executor unavailable at PLAN: stop with `EXECUTOR_UNAVAILABLE` before plan mutation.
- Sandbox command failure/timeout: persist failed evidence and do not advance as success.
- Tool capability unknown/disabled/mismatched/unapproved: deny before provider action.
- Provider/tool failure: return `FAILED`, never `SUCCEEDED`.
- Protected evaluation regression: block promotion.
- Database readiness failure: block deployment verification.
- Unsupported autonomous stage or authority boundary: return control to the operator.
- Project-policy resolution failure or attempted policy weakening: fail closed before protected execution/promotion.

## Security

No provider secret, production root secret or Vercel execution credential is shipped to the client or sandbox process.

User/model content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, filesystem root, tool capabilities, executable commands, protected evaluation or deployment state.

The major trust boundaries are now:

1. authenticated principal and server-owned authorization;
2. canonical Project identity and owner-scoped persistence;
3. inherited platform baseline + Project profile + approved Work Specification policy resolution;
4. approved Work Specification digest/acceptance map;
5. protected Project-to-workspace mapping (still to be integrated);
6. safe patch engine confinement/evidence;
7. server-owned command registry and Sandbox execution;
8. server-owned tool capability/approval registry;
9. protected evaluation/promotion policy;
10. human/release authority for unsupported destructive or production actions.

## Wave 2 integration contract

The next architecture slice must complete the safe composition of the Wave 1 primitives rather than invent new competing foundations.

Required order of truth:

```text
Authenticated principal
      ↓
Canonical Project.id
      ↓
Project-bound conversation / Work Specification / Engineering Run
      ↓
Protected workspace allocator + durable run workspace lineage
      ↓
Safe IMPLEMENT patch engine
      ↓
BUILD / TEST / VERIFY on the same implementation lineage
      ↓
Project-scoped capability checks for external actions
      ↓
App-builder protected evidence / promotion gate
      ↓
Operator review / release authority
```

End-to-end app-building is not considered architecturally complete until this lineage is proven through protected tests and observable evidence.
