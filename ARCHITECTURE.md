# Parallax 2.0 Architecture

Version: 2.9
Status: Authoritative

## System shape

Parallax 2.0 is a universal Expo / React Native client plus a Python FastAPI intelligence service backed by PostgreSQL, private immutable object storage, bounded provider adapters and isolated execution infrastructure. Conversation remains the primary product surface. Reason, Code, Work Specifications, canonical Project identity, execution, source lineage, worker recovery, deterministic/browser/visual validation, autonomous correction, tool authority, protected evaluation, authentication, observation telemetry and release evidence remain separate governed capabilities behind that surface.

```text
Expo / React Native client
  ├─ conversation + response state
  ├─ Project select/create
  ├─ Work Specification controls
  ├─ Code / Engineering Run status
  ├─ bounded-autonomy controls
  ├─ Google PKCE sign-in + owner access panel
  ├─ same-origin /p2-api web gateway
  └─ bounded API + governed Live Build / observability client
          │
          ▼
FastAPI intelligence service
  ├─ authentication + owner authorization
  ├─ canonical Project + Work Specification + Engineering Run authority
  ├─ durable worker lease/checkpoint/recovery
  ├─ protected IMPLEMENT + immutable source lineage
  ├─ exact-lineage BUILD / TEST / VERIFY
  ├─ browser / screenshot / visual validation
  ├─ bounded autonomous correction / convergence
  ├─ project-scoped GitHub + Vercel Preview delivery
  ├─ protected evaluation
  └─ migration-gated non-authoritative run-event projection + protected reads
          │
          ├────────────► isolated Vercel Sandbox execution
          ├────────────► private Vercel Blob immutable source objects
          ├────────────► hosted PostgreSQL / Supabase authoritative metadata
          └────────────► bounded provider plane
```

Wave 3 remains the deployment-verified app-builder execution architecture at the pre-production Wave 4 release boundary. Wave 4 Live Build/Observability source is integrated but production run-event persistence and protected observation remain explicitly migration/activation gated until release evidence records otherwise. Preview publication remains the ordinary autonomous provider ceiling; production promotion remains a separate governed release action.

## Core trust boundaries

The client owns presentation and interaction state. It does not own provider credentials, production root credentials, Project truth, authorization truth, Work Specification approval authority, accepted source lineage, worker leases/checkpoints, executable command definitions, protected validation/evaluation rules, run-event truth or deployment authority.

Live Build is an observer over server-owned facts. Code, diff, terminal/test evidence, provider identities, health and alerts render only from protected Project/run-scoped APIs and persisted evidence. `Pause View`, `Follow Live`, `Jump to Latest` and inspection selection do not mutate execution. Protected Pause/Resume/Cancel/Review remain separate commands.

Hosted web protected traffic uses same-origin `/p2-api/*` routing. Provider credentials, Vercel execution credentials and root access secrets never ship in the browser bundle.

Operational probes remain deliberately public: `/health` proves the FastAPI process can answer; `/ready` proves persistence can answer a database query. Protected application and observability surfaces remain behind private authentication.

## Observation architecture

`engineering_run_events` is an append-only non-authoritative projection. Project, Engineering Run/attempt, worker lease/checkpoint, source-lineage, provider and evaluation records remain authoritative.

Run events use canonical Project/run identity, idempotent event keys and monotonic per-run sequence. They never grant execution authority and never store raw source bytes. Resumable SSE uses durable sequence/`Last-Event-ID`; browser disconnect/reconnect does not own or stop the worker.

Protected source tree/file/diff reads resolve exact immutable lineages owned by the selected run. BUILD/TEST/VERIFY evidence reads are bounded and allowlisted. Secret-like excerpts, credentials, environment values, private-reasoning/scratchpad markers, raw provider payloads and unrestricted logs are redacted or unavailable before transport.

`PARALLAX_RUN_EVENTS_ENABLED` is a server-owned activation boundary. Only exact value `1` activates event emission and observability-route registration. Production activation requires the additive `engineering_run_events` migration first; build/preflight with activation enabled fails closed if the table is absent. Rollback is flag-first and does not require dropping durable event data.

## Identity, specification and execution authority

`Project.id` is canonical durable application identity. Conversation and Engineering Run binding use it. `workspace_ref` is opaque identity rather than a filesystem path or execution authority; `repository_ref` is repository identity rather than provider authority.

A Work Specification is an operator-controlled implementation contract. AI may draft it; only explicit protected mutation approves it. Each authoritative Code Engineering Run binds to one approved Work Specification revision/digest with stable server-derived acceptance IDs.

Protected lifecycle:

`SPECIFY -> PLAN -> IMPLEMENT -> BUILD -> TEST -> VERIFY -> REVIEW -> COMPLETE`

Protected validators require exact acceptance coverage and observable evidence. REVIEW/HUMAN_REQUIRED remains an operator boundary and is never inferred as autonomous completion by the observer.

## Protected app-builder runtime

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
Typed IMPLEMENT proposal + confined safe mutation
      ↓
Transactional acceptance of immutable source lineage
      ↓
BUILD / TEST / VERIFY on that exact lineage
      ↓
Browser / accessibility / console / network / layout validation
      ↓
Screenshot regression + bounded visual review
      ↓
Bounded correction / fresh exact-lineage revalidation / LKG convergence
      ↓
Project-scoped GitHub PR + Vercel Preview
      ↓
Protected app-builder evaluation from persisted evidence
      ↓
Operator REVIEW
```

No fresh-repository fallback is permitted after accepted IMPLEMENT lineage exists. Later stages and corrected candidates reconstruct exact accepted lineage. Safe mutation remains bounded by path, base digest, source/patch/result size, traversal/symlink/secret policy and transactional acceptance.

## Durable source lineage and execution

Authoritative source continuity is content-addressed across private immutable object storage and PostgreSQL lineage manifests/transactional heads. Source bytes are intentionally absent from PostgreSQL. Local filesystem roots are disposable materializations only.

Accepted IMPLEMENT validates exact parent lineage, verifies mutation artifacts and advances lineage transactionally. Stale/duplicate acceptance fails closed. BUILD/TEST/VERIFY execute registered commands in isolated Vercel Sandboxes reconstructed from accepted lineage, with deny-all network by default, empty application-secret environment and bounded observable evidence.

## Durable worker recovery

`engineering_worker_executions` remains the server-owned live-worker ownership/recovery record rather than a competing Engineering Run/source-lineage state machine. Leases use opaque owner identity, monotonic generation and bounded expiry; only the current generation has mutation/checkpoint authority.

Canonical checkpoints bind Project/run/Work Specification identity to bounded step, accepted/LKG lineage, evidence/dependency references and retry/progress state. Recoverable process loss resumes from durable checkpoints. Retry/no-progress/oscillation budgets remain bounded.

## Provider, evaluation and release boundaries

Provider authority resolves only after canonical authenticated Project resolution. Repository, connector, Preview target and credentials are server-owned. Models and clients cannot provide arbitrary endpoints, tokens, repositories or deployment projects.

Protected evaluation derives from persisted Project/spec/run/accepted-lineage/BUILD/TEST/VERIFY/provider facts. Equivalent candidates must satisfy protected baselines and negative cases; observed output cannot weaken scoring or authority.

Autonomous Project delivery ceiling is GitHub publication plus Vercel Preview. Deployment of Parallax itself is governed separately by exact-head validation, migration order, standing single-user promotion authority, rollback and post-deploy evidence.

## Accessibility and presentation

Normal product text, source, diff and bounded evidence remain selectable and semantically exposed. React Native Skia is decorative only and reduced-graphics mode preserves equivalent capability. Mobile uses focused reflow instead of a scaled desktop. Protected visual state never outruns authoritative runtime state.
