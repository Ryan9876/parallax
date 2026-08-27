# Parallax 2.0 Architecture

Version: 3.6
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
  ├─ bounded API client
  └─ governed Live Build / Observability client
          │
          ▼
FastAPI intelligence service
  ├─ Google identity verification + authorized-user allowlist
  ├─ signed browser-session boundary + bearer break-glass compatibility
  ├─ Project lifecycle and owner-scoped repository binding
  ├─ bounded repository intelligence + compatibility profiles
  ├─ exact-digest governed skill + Project service-binding registries
  ├─ objective-to-application orchestration + validated engineering memory
  ├─ governed engineering-agent adapter + evidence protocol
  ├─ bounded development-team orchestration
  ├─ independent evaluation + quality evidence
  ├─ bounded outcome routing + development economics
  ├─ bounded candidate competition + synthesis evidence
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
  ├─ protected evaluation + observable execution/provider evidence
  └─ Wave 4 non-authoritative run-event + protected observation read plane
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
          │               ├─ source lineage manifests + transactional heads
          │               └─ Wave 4 run events only after explicit migration + activation
          │
          └────────────► bounded provider plane
                          ├─ request-scoped Vercel OIDC → Vercel AI Gateway for hosted model traffic
                          ├─ Vercel Connect → short-lived GitHub App credential
                          ├─ GitHub branch/commit/PR publication
                          └─ project-scoped Vercel Preview deployment
```

Wave 3 remains the deployment-verified app-builder execution architecture at the pre-production Wave 4 release boundary. Wave 4 Live Build/Observability source is integrated but production run-event persistence and protected observation remain explicitly migration/activation gated until release evidence records otherwise. Wave 5 generalized application delivery is deployment-verified. Wave 6 S1-S5 are accepted on the governed Wave 6 integration branch but are not production deployments. Preview publication remains the ordinary autonomous provider ceiling; production merge/promotion remains outside ordinary autonomous Project execution.

## Core trust boundaries

### Client

The client owns presentation and interaction state. It does not own provider credentials, the production root credential, durable Project truth, durable authorization truth, Work Specification approval authority, accepted source lineage, worker leases/checkpoints, executable command definitions, tool capabilities, protected validation/evaluation rules, run-event truth or deployment authority.

Assistant text remains ordinary selectable React Native text. React Native Skia is decorative/optical only and reduced-graphics mode preserves equivalent product capability.

Hosted web protected traffic uses same-origin `/p2-api/*` routing to the API. Provider credentials, Vercel execution credentials and the root access secret are never shipped in the browser bundle.

### API

Routes call services/coordinators; services call repositories, execution adapters, lineage gateways, worker-recovery services, validation/correction controllers and bounded capability registries. Provider SDK details do not leak into public route contracts.

Operational probes remain deliberately public:

- `/health` proves the FastAPI process can answer;
- `/ready` always proves the persistence boundary can answer a database query and, in production, additionally proves the request-scoped Vercel runtime OIDC identity can exchange through the registered Connect connector to an exact repository-scoped GitHub credential.

Project, conversation, Work Specification, Engineering Run, worker state, Reason, Code, access-management, session and bounded-autonomy surfaces remain behind the private authentication boundary.

### External provider plane

Provider authority is resolved only after canonical authenticated Project resolution. Repository identity, connector identity, Preview target identity and credentials are server-owned registrations. Models and clients cannot provide arbitrary provider endpoints, tokens, repositories or deployment projects.

Hosted production model transport is also server-owned. A validated request-scoped Vercel runtime OIDC token may authenticate an OpenAI-compatible request to the fixed Vercel AI Gateway endpoint, but the token does not become generic model, network, tool or deployment authority. Model identity, escalation order, endpoint selection and credential admission remain bounded Parallax policy.

## Identity and access architecture

Google/Supabase proves interactive identity. Parallax decides application authorization through the server-owned `authorized_users` allowlist.

Each protected request resolves an `AccessPrincipal`. Project ownership is derived from that authenticated principal; caller-supplied owner identity is never trusted as authorization input.

RLS remains enabled on server-owned hosted tables where required and direct `anon` / `authenticated` table privileges are revoked for server-mediated control-plane data. FastAPI remains the application authorization layer.

`PARALLAX_ACCESS_TOKEN` is a server-only break-glass/automation credential. It is not the normal browser login path and is not forwarded into sandboxes or provider calls.

## Canonical Project identity

`Project.id` is the canonical durable application identity. A Project also carries authenticated owner identity, owner-local metadata, optional bounded `repository_ref`, opaque `workspace_ref = project:<id>`, lifecycle/status metadata and timestamps.

`workspace_ref` is identity, not a filesystem path or execution authority. `repository_ref` is repository identity, not Git/network/deployment authority.

Conversation and Engineering Run Project binding use the canonical Project ID. Existing historical rows may remain unbound where migration policy intentionally preserved prior state; new protected Code execution requires canonical Project binding.

No client, model, provider or execution adapter may create a competing durable Project identity for an already resolved Project.

## Governed workspace deletion and retention

User-visible deletion is a logical workspace-lifecycle operation, not an audit/evidence purge. `Conversation.deleted_at` and `Project.deleted_at` tombstone an item out of active reads while retaining the durable row needed to preserve protected provenance and historical evidence.

A conversation may be deleted only when no non-terminal Engineering Run is bound to it. A Project may be deleted only when no non-terminal Engineering Run is bound to the Project. These checks are server-owned and fail closed with conflict rather than letting client state hide live work.

Deleting a Project removes that Project and its bound conversations from active Project/conversation surfaces. It does not delete Engineering Runs, attempts, run events, Work Specification evidence, accepted source-lineage records/objects or immutable provider/evaluation evidence. It also never deletes the linked GitHub repository, pull requests, Vercel deployments or other external provider resources.

Project slug and repository identities are unique only among non-deleted Projects. A tombstoned Project therefore does not permanently reserve an owner-local slug/repository identity; a later replacement Project receives a new canonical `Project.id` and cannot inherit the deleted Project's run/source authority merely by reusing human-readable identity.

Deletion remains inside the existing authenticated FastAPI boundary. Project deletion is owner-scoped through canonical Project ownership. Historical unbound conversation compatibility retains the existing workspace-access semantics; this feature does not introduce a separate per-conversation ownership model.

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

Repository bootstrap is part of `EngineeringRuntimeComposition`. A missing root lineage is created from the exact owner-scoped repository through the protected source projection; an existing durable head is replayed instead of reinitialized. Production rollback-only canaries exercise this composition through `EngineeringRuntimeComposition.run()` itself and deliberately stop before stage mutation.

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

The private Blob adapter uses deterministic SHA-256 paths and verifies content after reads/writes. Transient HTTP transport failures are normalized inside the adapter and retried only within a hard bounded attempt count. An uncertain immutable write is reconciled by exact content-address read-back. Request-local caching may reuse only bytes already verified against the expected digest; that cache is disposable and never durable authority.

Accepted IMPLEMENT performs exact parent-lineage validation, verifies mutation artifacts against workspace bytes, advances lineage transactionally and cleans the disposable lease. Duplicate/stale acceptance fails closed.

Production source bootstrap additionally applies a lineage-safe repository projection before file bytes enter source packages or durable storage. Secret-sensitive paths are excluded before provider file reads; strict UTF-8, NUL, per-file, aggregate-size and digest contracts remain fail-closed.

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

## Wave 5 generalized application delivery

Wave 5 generalizes the protected app-builder architecture without introducing a second execution or authority path. Repository understanding, skill selection, service resolution, objective orchestration and engineering-memory reuse are typed evidence/admission layers in front of the existing canonical Project/Work Specification/Engineering Run/source-lineage runtime. The accepted protected runtime remains the sole mutation, execution, provider-delivery and REVIEW authority.

Repository intelligence consumes a bounded `RepositoryEvidenceSnapshot` bound to canonical Project, repository identity and source revision and emits a deterministic `RepositoryCompatibilityProfile`. The profile records repository shape, compatibility state, normalized signals, bounded blockers and inspectable command candidates. Repository files, manifests, scripts, comments and other source text remain untrusted evidence: they cannot grant commands, tools, capabilities, credentials, provider scope, deployment authority, approval or policy override. Ambiguous or unsupported evidence fails closed rather than guessing an application root or execution route.

Governed skills are immutable typed procedures admitted only by exact skill ID/version/content digest under server-owned policy. Skill selection requires the current objective kind, accepted repository shape/signals and an explicit server-owned capability snapshot. A skill may require capabilities but cannot create them. Application service needs resolve only through exact Project-scoped service bindings admitted by server policy for declared service/interface/adapter/feature contracts and opaque secret-slot identities; bindings never expose raw credentials to models, repository content or benchmark configuration.

Objective-to-application orchestration binds canonical Project/run identity, approved Work Specification revision/digest and acceptance IDs, exact repository revision/compatibility-profile digest, governed skill selection, Project service bindings, capability policy and bounded correction policy. Its `READY` or `HUMAN_REQUIRED` decision is deterministic admission evidence, not source-mutation, command, provider, deployment or approval authority. Missing capability, incompatible or ambiguous service binding, unsupported repository evidence or identity drift remains fail-closed.

Validated engineering memory is immutable provenance-bound evidence. Project-private memory is non-observable across Project boundaries by default. Cross-Project reuse is limited to explicitly approved sanitized/generalized content bound to exact memory identity/version/digest. Repository/profile drift, required-signal mismatch and evaluator-policy drift reject stale candidates. A memory HIT never changes the current Work Specification or evaluator threshold and always retains `fresh_validation_required=true`; memory cannot grant tools, service bindings, provider scope, execution, source mutation, deployment or approval.

The permanent Wave 5 generalization proof composes these accepted S1-S5 layers with the existing protected reference runtime and correction controller across materially different static/client-web, Python-service and workspace/monorepo shapes plus ambiguous and malicious negative fixtures. The proof verifies exact-lineage IMPLEMENT/BUILD/TEST/VERIFY, bounded fresh-lineage correction, governed GitHub/Vercel Preview delivery, process/delivery replay idempotency, privacy-safe reuse and the explicit `REVIEW` / `HUMAN_REQUIRED` ceiling. The S6 proof/evaluation layer itself is read-only evidence logic and owns no filesystem, source, command, provider, deployment or approval mutation surface.

## Wave 6 agent adapter and evidence protocol

Wave 6 S1 adds a provider-neutral engineering-agent protocol as a bounded evidence/admission layer in front of existing Parallax worker, source-lineage, validation and release authority. S1 is accepted on the Wave 6 integration branch; this section records its durable contract without claiming production deployment.

`AgentIdentity` binds an agent ID/version, adapter ID/version, provider kind and declared work/capability evidence. Declarations are descriptive evidence only; they cannot create server capabilities, credentials, network access, shell authority, source acceptance, validation authority, merge/deployment authority, approval or REVIEW authority.

`AgentTaskBinding` binds each task attempt to canonical Project ID, Engineering Run ID, exact Work Specification ID/revision/digest, exact server-owned acceptance IDs, operation/request identity, monotonically bounded attempt identity, exact agent-identity digest and optional source-lineage context. Result or checkpoint evidence that drifts from those bindings fails closed.

The protocol normalizes lifecycle states including accepted, started, running, checkpointed, completed, recoverable failure, terminal failure, timeout, cancellation and rejection. Admission explicitly distinguishes accepted, duplicate, identity mismatch, acceptance mismatch, source-context mismatch, stale attempt, revoked result, competing terminal result and invalid evidence. Duplicate/replay handling may recognize the same immutable evidence but cannot make a conflicting terminal result authoritative.

Agent evidence references are bounded typed references with optional exact digests. Usage observations distinguish `OBSERVED`, `UNAVAILABLE` and `UNKNOWN`; provenance distinguishes provider-observed, Parallax-observed and bounded estimates. Missing cost, token, request or duration evidence remains missing rather than being fabricated. Raw provider payloads, arbitrary URLs, credentials, secret handles, prompts, hidden reasoning and unbounded diagnostic content are not canonical agent evidence.

Reference adapters prove interchangeability and recovery semantics without adding provider authority. Adapter invocation is therefore labor orchestration input/output, not a second Engineering Run, worker lease, source-lineage, validation or release state machine. S2 and later orchestration layers must compose with this protocol and the existing durable worker lease/checkpoint/recovery system rather than supersede it.

## Wave 6 dynamic development-team orchestration

Wave 6 S2 composes accepted S1 agent evidence into deterministic bounded team formation and scheduling. It remains subordinate to the canonical Project, Work Specification, Engineering Run, worker lease/checkpoint/recovery, source-lineage, validation, provider and release authorities.

Server-owned team policy admits only exact S1-conforming agent identities whose declared work/capability evidence satisfies the required task domains. The planner chooses the smallest adequate team: one agent when one eligible agent covers the objective, otherwise a bounded multi-agent team only when decomposition is valid and within configured limits. Agent declarations never create capabilities or authorization.

Work is represented as bounded dependency-aware assignments. Cycles, unknown dependencies, duplicate identities, impossible coverage and unsafe graph construction fail closed. Tasks that share a server-derived coordination domain are conservatively serialized even when their declared file hints appear disjoint; parallelism is allowed only where dependency and coordination evidence support it.

Assignment, dispatch and replay identity are deterministic. Every dispatched unit composes the accepted S1 `AgentTaskBinding`/result-admission contract rather than inventing a second task/result authority path. A team result can preserve bounded agent outcome and usage evidence but cannot accept canonical source lineage, advance an Engineering Run, satisfy protected validation, or decide final candidate quality.

Recovery/reassignment is driven by Parallax-owned durable worker evidence rather than agent self-report. Reassignment preserves the logical assignment while advancing an explicit generation so stale generations fail closed. Team size, parallelism, retry, replan, reassignment and no-progress behavior are bounded; exhaustion produces explicit bounded failure/HUMAN_REQUIRED evidence rather than unbounded agent creation or looping.

S2 creates no credential, provider, tool, filesystem, source-mutation, merge/deployment, approval or REVIEW authority. S4/S5 may consume orchestration evidence, but cannot treat team formation or successful labor completion as canonical acceptance.

## Wave 6 independent evaluation and quality judgment

Wave 6 S3 establishes an independent, provenance-bound quality-evidence layer for agent-produced candidates. It is structurally below protected deterministic validation and above no canonical acceptance boundary.

`CandidateBinding`-equivalent identity binds exact Project ID, Engineering Run ID, Work Specification ID/revision/digest, stable acceptance IDs, candidate/source-lineage digest, candidate revision/attempt identity and producer-agent identity digest. Protected validation evidence must bind the same exact candidate and acceptance map. Missing, failed, stale, mismatched or cross-Project protected evidence blocks support before qualitative judgment is considered.

Evaluator identity is explicit and structurally distinct from producer identity. Exact self-evaluation cannot satisfy independence. A server-owned immutable evaluator policy binds policy ID/version/digest, admitted evaluator identities, approved qualitative dimensions, allowed evidence kinds, bounded evidence counts, score rules/floors and human-escalation behavior. Repository, source, agent and model text cannot change this policy or acceptance IDs.

Qualitative evidence is bounded to typed references and concise safe findings. Canonical evaluator evidence excludes raw provider payloads, credentials, prompts, hidden reasoning, arbitrary URLs, executable commands and authority-bearing instructions. Project-private evidence cannot cross a Project boundary unless it was already admitted through a separate sanitized/generalized-memory authority.

Final S3 outcomes are bounded to `SUPPORTED`, `DETERMINISTIC_BLOCKED`, `NOT_INDEPENDENT`, `INSUFFICIENT_EVIDENCE`, `POLICY_REJECTED` and `HUMAN_REQUIRED`. `SUPPORTED` means only that independent evidence supports the exact candidate under the exact bound evaluator policy; it does not accept lineage, complete REVIEW, select a provider or candidate winner, authorize spending, merge, deploy or mutate protected run state.

Evaluation replay uses a deterministic fingerprint over exact candidate, producer/evaluator identity, policy and admitted evidence. Exact replay is duplicate-safe. Changed evidence/candidate/evaluator/policy creates a distinguishable identity. Competing records for one fingerprint fail closed rather than silently choosing a winner.

S4 may consume S3 output only as quality evidence combined with S1/S2 and protected deterministic facts. S5 candidate competition remains a later bounded policy layer and cannot inherit acceptance authority merely from S3 support.

## Wave 6 outcome routing and development economics

Wave 6 S4 extends the existing development optimization controller with deterministic, provenance-bound routing evidence for already-admissible engineering strategies. It is accepted on the Wave 6 integration branch and remains an evidence/decision layer rather than a new execution, source-lineage, provider or release authority path.

`RoutingContext` binds canonical Project and Engineering Run identity, exact Work Specification ID/revision/digest and acceptance IDs, accepted S1/S2/S3 protocol/policy identity, exact server-owned S4 routing-policy identity/version/digest and a bounded decision sequence. `DevelopmentStrategy` binds an already-possible single-agent or bounded-team strategy to exact admitted agent/team identities, work profile and descriptive capability/provider/model classes; those declarations cannot create authority.

Outcome evidence preserves protected deterministic-validation status, exact S3 evaluation-record identity, completion state and bounded economic observations such as duration, cost, retry/reassignment/replan and human-intervention burden. Evidence states distinguish observed, estimated, unavailable, unknown, stale and invalid values. Trusted observed evidence requires admitted provider/Parallax provenance; agent/model/repository self-report cannot promote itself into an observed fact. Unknown or unavailable evidence remains explicit and is never treated as zero, free, fast or successful.

Eligibility is structurally computed before economics. Project/run/spec/acceptance drift, S1/S2 dependency drift, missing capability/authority admission, protected deterministic failure, rejected or insufficient S3 evaluation, unresolved `HUMAN_REQUIRED`, stale/invalid mandatory telemetry, cross-Project private evidence or server-policy mismatch excludes a strategy before cost/time scoring. A cheaper or faster strategy cannot purchase correctness, safety, privacy or evaluator-policy admission.

Only eligible strategies are normalized under immutable server-owned economic policy. Quality/confidence floors are non-tradeable; scoring components remain inspectable; estimates are explicitly discounted/controlled; deterministic strategy identity breaks ties. Missing or contradictory evidence produces a bounded conservative fallback, bounded exploration only among already-admissible strategies, `INSUFFICIENT_EVIDENCE`, `POLICY_REJECTED` or `HUMAN_REQUIRED` according to policy rather than fabricated certainty.

Routing decisions are fingerprinted over the exact context, policy, strategies and admitted evidence. Exact replay is duplicate-safe; policy/evidence/strategy drift yields a distinguishable decision; competing records fail closed. Safe downstream serialization for S5/S6 exposes bounded provenance, eligibility reasons, components, selected/fallback strategy identity and decision fingerprints while structurally exposing no provider invocation, spending, capability grant, source-lineage acceptance, Engineering Run transition, merge/deploy, REVIEW completion or candidate-winner authority.

S4 was deliberately re-homed into the existing optimization-controller/test surfaces after final validation exposed the protected 512-entry repository-tree ceiling. The accepted correction preserved that fail-closed provider/source projection bound rather than weakening it. S5 may consume S4 only as accepted routing/outcome evidence and must independently preserve candidate lineage, validation and evaluator authority boundaries.

## Wave 6 candidate competition and synthesis

Wave 6 S5 extends the existing optimization controller with selective, bounded competition between already-admissible implementation candidates. It is accepted on the governed Wave 6 integration branch and remains an evidence/decision layer; it does not create source-lineage, provider, spending, Engineering Run, approval, merge/deploy or REVIEW authority.

Competition is invoked only under immutable server-owned policy when accepted S2/S3/S4 evidence justifies the added bounded cost/time. Each candidate is isolated by exact canonical Project/run/Work Specification identity, stable acceptance IDs, exact candidate/source-lineage identity, producer identity, deterministic-validation evidence, independent-evaluator identity/policy and admitted routing/economic evidence. Candidate declarations, agent confidence, votes or low cost cannot substitute for those bindings.

Protected deterministic validation is authoritative before comparison. A deterministically failed, stale, cross-Project, policy-mismatched or insufficiently evaluated candidate is ineligible regardless of qualitative score, agent recommendation or economic advantage. S3 evidence used for comparison must remain structurally independent from the candidate producer and bind the exact candidate/evaluator policy.

Winner selection is deterministic, provenance-bound and replayable under exact competition/routing/evaluator policy versions. Candidate, attempt, synthesis, elapsed-time, cost and no-progress behavior are bounded. Exhaustion resolves to a bounded safe fallback, no-selection or `HUMAN_REQUIRED`, not unbounded alternative generation.

Synthesis never splices unvalidated fragments directly into canonical lineage. A synthesis request produces a distinct candidate identity/source lineage that must pass fresh exact-lineage BUILD/TEST/VERIFY, protected deterministic validation and fresh independent evaluation before it can become eligible for comparison. Competition records and their safe downstream S6 projection expose bounded evidence only and confer no canonical acceptance authority.

## Project-scoped tool authority

The tool layer defines immutable typed capabilities, authority requests, approvals, decisions, results and audit records. A server-owned registry is authoritative. Model/user input cannot create or widen capabilities.

Authorization requires exact registered Project/tool/action matching. Destructive actions require explicit approval by invariant. Generic shell, arbitrary command, raw HTTP, arbitrary URL/header/environment and unregistered network escape hatches are rejected.

Results distinguish `DENIED`, `FAILED` and `SUCCEEDED`; provider failure or authority denial can never be represented as success.

## Bounded GitHub and Vercel Preview delivery

Production source delivery is selected from a server-owned target registry after owner-scoped canonical `Project.repository_ref` resolution.

Each registered target binds exact repository identity/GitHub repository ID, production branch identity, Vercel Preview project/team identity, a GitHub Vercel Connect connector reference and a Vercel credential environment-variable reference.

The current Parallax self-target uses `github/parallax-runtime` and `vercel:preview:parallax` capability identities.

GitHub credentials are short-lived Vercel Connect credentials obtained from Vercel-provided OIDC. A slash-bearing connector identity is serialized as one percent-encoded URL path parameter at the Connect wire boundary. Before use, GitHub must prove the minted credential can access the exact canonical repository; mismatched repository reach fails closed.

Vercel's build OIDC and Functions runtime OIDC are distinct trust surfaces. Production autonomous requests take their Vercel identity only from the per-request `x-vercel-oidc-token` header and explicitly inject it into the registered Connect credential provider. The build-time `VERCEL_OIDC_TOKEN` is not a production runtime fallback. Missing or malformed request OIDC therefore fails closed instead of silently selecting a broader or static credential path.

Vercel Preview credentials are scoped per registered target project. Request-scoped provider composition receives only the selected target/credential, preventing one Project from inheriting another Project's provider authority.

Publication is replay-aware and durable: request/process recreation resolves the accepted delivery record and does not duplicate branch/commit/PR/Preview mutation when the same exact action was already accepted.

The Parallax self-development API release path performs production-only read-only provider and source/durability preflights before a new production deployment may become READY. Build-time preflights verify the build identity and registered provider/source/storage boundaries. Production `/ready` separately exercises the Functions runtime identity through the real Vercel Connect exchange and exact registered GitHub repository scope, preventing a successful build-time exchange from masking an unavailable runtime credential path. Preview deployments intentionally skip production-only provider/storage authority.

Preview remains the autonomous deployment ceiling for Parallax-developed Projects. Parallax's own production promotion/merge remains a governed release boundary. Standing single-user release authorization does not give Project runtime autonomous production-deployment authority.

## App-builder evaluation and observability

The protected app-builder evaluator consumes evidence derived from persisted Project, Work Specification, Engineering Run, source-lineage, BUILD/TEST/VERIFY, provider action and provider-audit facts. It does not synthesize success and does not rerun provider mutations simply to evaluate them.

Evidence is bound to canonical Project ID, approved specification revision/digest, run ID, accepted source lineage/content digest, tool capability/request/result/audit identities, published source revision/PR and Preview identity/status where applicable.

Secret-bearing evidence, raw provider responses, credentials, headers/cookies/environment, hidden reasoning/scratchpad and unbounded logs are forbidden.

Scoring remains deterministic with critical-failure semantics. Wrong Project/spec/digest/lineage/stage/provider/Preview/evidence identity, forbidden production authority, denial/failure misrepresentation and unrelated/fresh source fail closed.

The permanent protected reference proof recreates process/runtime composition between meaningful stages and proves durable worker reassignment, stale-worker rejection, exact lineage/LKG reconstruction, no duplicate implementation mutation, no duplicate publication, browser/visual precedence, bounded correction/convergence and correct retry/replay behavior.

## Wave 4 run-event observation boundary

Wave 4 introduces an append-only, non-authoritative Project/run event projection. It is an observation layer only; Engineering Run state, attempts, accepted source lineage, worker leases/checkpoints, provider action/audit evidence and protected evaluation remain authoritative.

Source integration alone does not activate this projection in production.

Activation requires both:

1. the migration containing `engineering_run_events` to be applied through the governed production migration process; and
2. the server-owned environment value `PARALLAX_RUN_EVENTS_ENABLED` to equal exactly `1`.

When the flag is absent or any value other than exact `1`, the Engineering Run route does not attach `PersistentRunEventSink`. The authoritative Wave 3 runtime therefore has no dependency on an unapplied Wave 4 observation table.

The production build guard mirrors the same boundary:

- Wave 4 disabled → PASS while recording that the migration is unapplied/not activated;
- Wave 4 enabled → require `engineering_run_events` to exist, otherwise block production cutover.

This gate prevents an environment toggle from silently activating telemetry against a missing schema and prevents source integration from being misreported as deployment/activation.

### Protected observation read plane and Live Build

Authenticated observation routes expose persisted event replay, resumable SSE using durable sequence/`Last-Event-ID`, exact-lineage source tree/file/diff reads and bounded BUILD/TEST/VERIFY attempt evidence. The client is an observer over those server-owned facts: pipeline state, health, retries, failures, provider identities and alerts are projections only and cannot advance Engineering Run state.

`Follow Live`, `Pause View`, `Jump to Latest`, tab selection and source/evidence selection are observation controls only. Browser disconnect/reconnect does not own or stop the worker, and switching Project/conversation/run clears observer-local selections before new protected reads begin. No generic shell, filesystem mutation, arbitrary command execution or provider mutation surface is introduced by Live Build.

Privacy filtering occurs before transport. Credential-like excerpts, bearer/private-key patterns, secret-bearing material, raw provider payloads, environment values, hidden reasoning/private scratchpad markers and unbounded logs are redacted or unavailable rather than delegated to client rendering.

## Persistence

SQLAlchemy 2 supports SQLite development and PostgreSQL hosted environments through `DATABASE_URL`. Production uses the dedicated Parallax Supabase PostgreSQL project. Schema evolution is migration-driven under `services/api/migrations`; production startup performs no implicit DDL.

Active production durable schema includes conversations, messages, work specifications, engineering runs, engineering attempts, engineering worker executions, authorized users, projects, source lineage manifests and source lineage heads. Conversation and Project rows carry nullable `deleted_at` tombstones; active reads exclude tombstoned rows and conversations bound to tombstoned Projects. Owner-local Project slug/repository uniqueness is enforced by partial unique indexes over active rows only.

`engineering_run_events` is a Wave 4 optional observation schema and is not considered active production persistence until its migration and activation gate are both completed.

Project foreign keys bind conversations and Engineering Runs where required. Source-lineage and worker-execution tables use RLS as defense in depth and revoke direct `anon` / `authenticated` table privileges. Server-owned control-plane tables intentionally require no direct-client policy; FastAPI remains the application authorization boundary.

## Reason and model routing

Reason remains provider-independent and bounded by durable context. Later explicit user corrections supersede conflicting earlier assistant assumptions.

Scope routing proposes `CONTINUE`, `CLARIFY` or `SPEC_AMENDMENT`; protected server policy owns the transition. Invalid, secret-bearing, hidden-reasoning or scope-incompatible candidates are rejected/escalated rather than exposed.

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`
2. `openai/gpt-5.6-terra`
3. `openai/gpt-5.6-sol`

For hosted production model traffic, canonical model IDs remain unchanged while transport is explicit: an admitted request-scoped Vercel runtime OIDC token is supplied to the OpenAI-compatible Vercel AI Gateway endpoint `https://ai-gateway.vercel.sh/v1`. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Deliberate server-owned `DSPY_API_BASE` / `DSPY_API_KEY` configuration remains the explicit override path. Without an admitted request OIDC token or such an explicit override, production model construction fails closed; it does not silently fall back to direct OpenAI.

Request-scoped OIDC is propagated only through bounded request context into downstream DSPy construction for conversation scope/reason, Work Specification drafting and protected implementation generation. Credentials are excluded from prompts, traces, persisted evidence, client payloads, source packages and sandboxes. Operational logs may record sanitized transport/model identity such as `transport=vercel_ai_gateway` and the canonical model ID, but never the credential.

DSPy operates in development specification compilation. Promotion validates the committed compiled plan and protected acceptance map deterministically; stochastic regeneration is not itself a promotion oracle.

## Deployment topology

Two authoritative Vercel projects deploy from the same repository:

1. Web `parallax` — root `apps/client`, Expo static export.
2. API `parallax-api` — root `services/api`, FastAPI via `api/index.py`.

`main` is the production source branch. Feature/integration branches create previews. Path-aware ignore behavior may suppress redundant builds when a commit does not affect a deployable root. An API-only production release may therefore deploy a new API SHA while intentionally preserving the existing verified client artifact.

The Vercel Sandbox execution plane, private Blob store and Vercel Connect connectors are runtime infrastructure, not additional long-lived Parallax application deployments.

Release promotion requires exact-head CI, relevant Preview evidence, migration readiness, production prerequisite verification, exact production deployment SHA, health/readiness/auth-boundary checks, runtime-error inspection and evidence-based state recording. For the Parallax API, production build preflights verify provider scope, bounded projected source, private Blob/durable lineage and the production runtime-bootstrap composition before cutover; production readiness then independently verifies the request-scoped runtime Connect exchange. Model-routing releases additionally require an authenticated exact-deployment request that exercises the hosted model path and verifies sanitized provider-transport evidence after cutover.

A green Preview is not production deployment evidence. Production-only preflights do not replace post-deploy smoke/observability checks.

While Parallax remains effectively single-user, `PROJECT-CONSTITUTION.md` v1.4 provides standing authority to promote an already validated Parallax release/hotfix without another per-release approval request. The authority expires when additional real users begin relying on production and never waives the release gates above.

## Parallel development and Control Tower

Parallel development is governed by `PROJECT-CONSTITUTION.md`, `PARALLEL-DEVELOPMENT.md` and GitHub as operational authority for active workstreams, branches, PRs, CI/evaluation evidence and integration state.

Workers develop concurrently on isolated branches. Interacting candidates are integrated serially at authoritative boundaries and cumulative protected gates are rerun after material composition changes.

Source-integrated future-wave code must not be treated as deployed/active merely because it is present on an integration branch or `main`; migration, release and activation state remain separate authoritative facts.

## Failure degradation

- identity provider unavailable, unauthorized or revoked: fail closed;
- invalid browser session: return to identity gate without retaining provider/root credentials;
- no approved Work Specification: block Code activation;
- Project lookup outside authenticated owner scope: fail as not found;
- Project/spec/run/source-lineage mismatch: block protected progress;
- conversation/Project deletion with a non-terminal Engineering Run: return conflict and preserve the active item/evidence;
- deletion of a tombstoned conversation/Project through active read scope: resolve as not found rather than reviving hidden state;
- agent task/result/checkpoint binding mismatch, stale/revoked attempt or competing terminal evidence: reject agent evidence and advance no canonical authority;
- team graph cycle, impossible capability coverage, unsafe coordination overlap or orchestration bound exhaustion: fail closed or return bounded HUMAN_REQUIRED evidence; do not create unbounded agents or parallelism;
- evaluator self-identity, policy drift, deterministic validation failure, insufficient/mismatched/cross-Project evidence or competing replay record: reject/normalize to the bounded S3 failure outcome; never synthesize support;
- routing context/policy/dependency drift, deterministic/S3 rejection, untrusted/stale/invalid/cross-Project economic evidence or contradictory routing records: exclude the affected strategy before economics and return bounded fallback, insufficient evidence, policy rejection or HUMAN_REQUIRED; never optimize around a protected failure;
- competition context/policy/candidate drift, deterministic candidate failure, producer/evaluator identity conflict, stale or ineligible routing evidence, cross-Project evidence, unvalidated synthesis or replay conflict: disqualify the affected candidate or stop with bounded fallback/no-selection/HUMAN_REQUIRED; never manufacture a winner;
- durable lineage unavailable or compare-and-swap stale: accept no mutation;
- transient private-Blob transport failure: retry only within the bounded adapter policy, then fail as object-store/write failure rather than escaping raw transport errors;
- invalid source patch or workspace escape: mutate nothing and return bounded failure evidence;
- Sandbox unavailable/failure/timeout: persist failure evidence and do not advance as success;
- expired/stale worker lease: reject checkpoint/mutation authority;
- recoverable process loss: classify, stall and resume/reassign from the durable canonical checkpoint within bounds;
- true specification/authority/credential boundary: enter `HUMAN_REQUIRED` rather than disguising it as ordinary retry;
- deterministic browser/accessibility/console/network/layout failure: block pass; visual or independent evaluator judgment cannot override it;
- regressive/equal/no-progress/oscillating correction: preserve last-known-good and stop/retry only within protected bounds;
- unknown change impact or incomplete reuse/cache provenance: discard optimization and run the conservative/full path;
- capability unknown/disabled/mismatched/unapproved: deny before provider action;
- provider target/credential/repository mismatch: fail before mutation;
- missing/invalid production request OIDC or failed runtime Connect exchange/scope verification: fail production readiness and autonomous repository bootstrap without static-credential fallback;
- missing/invalid production model request OIDC, or failure of the fixed hosted Gateway transport without an explicit server override: fail the model request; never silently select direct OpenAI;
- malformed connector wire identity or production provider/source/durability/bootstrap preflight failure: fail the candidate production build before cutover;
- provider failure: return `FAILED`, never `SUCCEEDED`;
- replay of an already accepted exact provider action: resolve durable delivery rather than duplicate mutation;
- protected evaluation regression: block promotion;
- database readiness failure: block deployment verification;
- Wave 4 run events disabled: run authoritative Wave 3 path without event projection;
- Wave 4 run events enabled without migrated table: block production cutover;
- unsupported destructive or production authority outside an active explicit/standing authorization: return control to the operator.

## Security invariants

No provider secret, production root secret or Vercel execution credential is shipped to the client or sandbox process.

User/model/agent/evaluator content cannot redefine authentication, Project ownership, Work Specification approval, required acceptance criteria, filesystem root, accepted source lineage, worker ownership/generation/checkpoint authority, deterministic validation precedence, team-orchestration policy, evaluator policy, routing/economic policy, competition/synthesis policy, correction/LKG policy, tool capabilities, executable commands, registered provider targets, hosted model endpoints/credentials, protected evaluation, run-event activation or deployment state.

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
11. exact-bound engineering-agent task identity plus bounded adapter/result/checkpoint evidence admission;
12. server-owned bounded development-team eligibility/dependency/coordination/reassignment policy;
13. independent evaluator identity plus exact server-owned evaluator policy and deterministic-validation precedence;
14. server-owned outcome-routing eligibility/economic policy with provenance-bound evidence and non-tradeable correctness floors;
15. server-owned candidate-competition/synthesis policy with exact-lineage isolation and fresh-validation requirements;
16. server-owned tool capability registry;
17. server-owned provider target/credential registry, request-scoped runtime OIDC identity, fixed hosted model transport and encoded connector wire contract;
18. persisted provider action/audit and replay identity;
19. protected evaluation/promotion policy;
20. optional non-authoritative run-event projection behind migration + exact activation flag;
21. governed logical workspace deletion with retained protected evidence and external-provider separation;
22. governed production release authority plus distinct fail-closed build-time provider/source/durability/bootstrap preflights and runtime Connect/model-routing verification.

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

## Deployed Wave 3 architecture

Wave 3 extends the protected app-builder loop through:

`approved objective/spec -> PLAN -> repository/durable-lineage bootstrap -> typed proposal -> protected mutation -> same-lineage BUILD/TEST/VERIFY -> browser exercise -> deterministic DOM/accessibility/console/network/layout checks -> screenshot regression -> bounded multimodal visual review -> bounded correction/retry with LKG -> Git/Preview -> protected evaluation -> operator review`

Deterministic failures are authoritative over visual judgment. The controller preserves last-known-good state and enforces retry, churn, runtime, resource, no-progress and oscillation bounds.

Worker states include `RUNNING`, `PROGRESSING`, `CHECKPOINTED`, `STALLED`, `RECOVERING`, `REASSIGNED`, `HUMAN_REQUIRED`, `READY_FOR_INTEGRATION` and terminal success/failure. Bounded leases, meaningful-progress checkpoints and single-writer recovery permit process loss/reassignment without duplicate mutation or corrupted lineage.

The same protected architecture governs Parallax self-development and every Project Parallax develops. Wave 4 observation capability may extend visibility around this runtime, but it does not become authoritative over it.