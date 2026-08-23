# Wave 2 provider-action integration map

Workstream: `#62` / `P2-V0.15.4`

This package is a provider-specific execution layer underneath the accepted Wave 1 `ToolCapabilityRegistry`. It is not a second authority system and it does not own cumulative app-builder orchestration.

## #59 — canonical Project binding

- `ProviderProjectBinding.project_ref` and `VercelPreviewTarget.project_ref` must be populated from canonical `Project.id` after authenticated owner-scoped resolution.
- `repository_ref` must come from server-resolved Project/provider configuration and remain `github:owner/repository` identity metadata; it does not grant capability.
- Never substitute `Project.workspace_ref` for `project_ref`, a repository identity, or execution authority.
- New provider-backed app-building work requires #59's canonical Project binding. Historical/unbound rows may remain readable under #59's compatibility rules but must not be used to authorize new provider actions.

## #60 — source/workspace lineage

#60's validated contract exposes `ProjectRunIdentity(project_id, run_id)`, a narrow `SourceProvider.load(ProjectRunIdentity) -> SourcePackage` initialization seam, and immutable `SourceLineage` receipts carrying `project_id`, `run_id`, `lineage_id`, and `content_digest`.

- Adapt an accepted #60 `SourceLineage` directly as:
  `AcceptedSourceLineage(project_id=lineage.project_id, run_id=lineage.run_id, lineage_id=lineage.lineage_id, content_digest=lineage.content_digest)`.
- `AcceptedSourceLineage.lineage_id` uses #60's protected `src:<sha256>` identity form and is carried together with the content digest in #62 evidence.
- GitHub commit, pull-request publication, and Vercel preview creation reject a lineage whose `project_id` does not equal the provider action's canonical `project_ref` before provider mutation.
- Serialized Integration should additionally construct the lineage from the same persisted Engineering Run identified by #59/#60; #62 preserves `run_id` for that exact binding rather than inventing a provider-local run identity.
- A #62 GitHub source adapter can implement #60's narrow `SourceProvider` by resolving already-authorized server-side Project/repository configuration and returning a bounded `SourcePackage`. Caller/model input must never select a filesystem root, repository URL, credential, or generic transport.
- `commit_accepted_lineage` requires the exact accepted lineage plus an expected parent provider revision. Pull-request creation requires the exact published head revision plus that same accepted lineage.
- A resulting GitHub commit or PR revision is a provider publication identity, not a replacement for #60's immutable content lineage.
- Vercel preview creation must bind the published source revision to the same accepted lineage; preview success cannot replace or mutate the lineage receipt.

## #61 — protected IMPLEMENT runtime

- #61 owns generation, proposal validation, safe patch application, idempotency, and the protected IMPLEMENT transition.
- #61 should consume #60's protected allocator/lineage receipt first; #62 may publish only the content represented by that accepted receipt.
- `GitHubCommitFile` values are publication material, not model mutation authority.
- `applied: true`, `COMMIT_WRITTEN`, pull-request creation, or preview success must never bypass #61's existing protected IMPLEMENT validator or stage policy.
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
