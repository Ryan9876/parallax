# Wave 2 provider-action integration map

Workstream: `#62` / `P2-V0.15.4`

This package is a provider-specific execution layer underneath the accepted Wave 1 `ToolCapabilityRegistry`. It is not a second authority system and it does not own cumulative app-builder orchestration.

## #59 — canonical Project binding

#59's validated runtime contract persists canonical `Conversation.project_id` and server-derived immutable `EngineeringRun.project_id` for new Code work. New strict runs leave `workspace_ref` unset until #60 supplies server-owned lineage.

- `ProviderProjectBinding.project_ref` and `VercelPreviewTarget.project_ref` must be populated from authenticated owner-scoped canonical `Project.id`, normally the persisted `EngineeringRun.project_id` for the publishing run.
- `repository_ref` must come from server-resolved Project/provider configuration and remain `github:owner/repository` identity metadata; it does not grant capability.
- Never substitute `Project.workspace_ref`, caller input, or repository metadata for canonical `project_ref` or execution/provider authority.
- Historical `HISTORICAL_UNBOUND` rows may remain readable under #59's compatibility rules but must not authorize new #62 provider actions.

## #60 — source/workspace lineage

#60's validated contract exposes `ProjectRunIdentity(project_id, run_id)`, a narrow `SourceProvider.load(ProjectRunIdentity) -> SourcePackage` initialization seam, and immutable `SourceLineage` receipts carrying `project_id`, `run_id`, `lineage_id`, and `content_digest`.

- Adapt an accepted #60 `SourceLineage` directly as:
  `AcceptedSourceLineage(project_id=lineage.project_id, run_id=lineage.run_id, lineage_id=lineage.lineage_id, content_digest=lineage.content_digest)`.
- `AcceptedSourceLineage.lineage_id` uses #60's protected `src:<sha256>` identity form and is carried together with the content digest in #62 evidence.
- GitHub commit, pull-request publication, and Vercel preview creation reject a lineage whose `project_id` does not equal the provider action's canonical `project_ref` before provider mutation.
- Integration must construct the lineage from the same persisted Engineering Run identified by #59/#60; #62 preserves `run_id` for that exact binding rather than inventing a provider-local run identity.
- A #62 GitHub source adapter can implement #60's narrow `SourceProvider` by resolving already-authorized server-side Project/repository configuration and returning a bounded `SourcePackage`. Caller/model input must never select a filesystem root, repository URL, credential, or generic transport.
- `commit_accepted_lineage` requires the exact accepted lineage plus an expected parent provider revision. Pull-request creation requires the exact published head revision plus that same accepted lineage.
- A resulting GitHub commit or PR revision is a provider publication identity, not a replacement for #60's immutable content lineage.
- Vercel preview creation must bind the published source revision to the same accepted lineage; preview success cannot replace or mutate the lineage receipt.

## #61 — protected IMPLEMENT runtime

#61's validated runtime requires exact Project/run/base-lineage identity before mutation, validates the generated proposal against the server-owned acceptance map, applies Wave 1 safe patches, accepts the resulting #60 source lineage, and only then invokes the existing protected IMPLEMENT validator/state machine.

- #62 publication must start from the exact accepted post-mutation #60 `SourceLineage` represented by #61's immutable `ImplementationLineageReceipt`; do not publish from a pre-IMPLEMENT checkout or an unaccepted patch result.
- The receipt's canonical Project/run/source-lineage identity must correspond to #62 `AcceptedSourceLineage.project_id`, `.run_id`, `.lineage_id`, and `.content_digest`.
- `GitHubCommitFile` values are publication material derived from that accepted lineage, not model mutation authority.
- `applied: true`, `COMMIT_WRITTEN`, pull-request creation, or preview success must never bypass #61's protected IMPLEMENT validator, durable stage transition, or idempotency policy.
- #61's same-lineage rule also applies after publication: BUILD/TEST/VERIFY must reconstruct the exact accepted lineage rather than silently falling back to an unrelated fresh checkout.
- The branch/commit/PR/preview path is publication after accepted IMPLEMENT, not implementation generation or protected-stage approval.

## #46 — protected app-builder evaluation

Map only bounded safe evidence into #46 observation/evidence contracts:

- provider/tool/action identity;
- canonical Project/repository identity digest;
- source revision;
- exact accepted `lineage_id` plus content digest;
- branch/commit/PR/deployment result identity;
- normalized result status/code;
- safe GitHub PR or `*.vercel.app` preview URL when needed;
- Wave 1 audit outcome and request/result digests.

Do not map raw source file contents, provider responses, credentials, authorization headers, environment values, cookies, request bodies, hidden reasoning, or other secret-bearing state into protected evaluation evidence.

## Authority and release ceiling

- Tool/action identity is fixed by each service method and authorized through Wave 1 before provider invocation.
- Denial does not call the provider; provider failure remains a failed audit outcome.
- Vercel preview is the autonomous ceiling for this wave.
- Production promotion, merge, release, environment/secret mutation, alias/domain mutation, and deployment verification remain Integration/operator authority.
