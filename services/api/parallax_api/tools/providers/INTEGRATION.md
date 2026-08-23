# Wave 2 provider-action integration map

Workstream: `#62` / `P2-V0.15.4`

This package is a provider-specific execution layer underneath the accepted Wave 1 `ToolCapabilityRegistry`. It is not a second authority system and it does not own cumulative app-builder orchestration.

## #59 — canonical Project binding

- `ProviderProjectBinding.project_ref` and `VercelPreviewTarget.project_ref` must be populated from canonical `Project.id` after authenticated owner-scoped resolution.
- `repository_ref` must come from server-resolved Project/provider configuration and remain `github:owner/repository` identity metadata; it does not grant capability.
- Never substitute `Project.workspace_ref` for `project_ref`, a repository identity, or execution authority.
- Historical/unbound Project compatibility remains #59's concern. Provider actions should not run until a canonical Project is resolved.

## #60 — source/workspace lineage

- Map #60's accepted immutable source-lineage identity into `AcceptedSourceLineage(lineage_ref, content_digest)`.
- GitHub source reads provide a narrow source-provider seam that #60 can use for repository-backed materialization; callers still cannot select a filesystem root.
- `commit_accepted_lineage` requires the accepted lineage plus an expected parent source revision. The provider layer must not label unrelated content as that lineage.
- A resulting GitHub commit revision is a provider publication identity, not a replacement for #60's content lineage contract.

## #61 — protected IMPLEMENT runtime

- #61 owns generation, proposal validation, safe patch application, idempotency, and the protected IMPLEMENT transition.
- #62 may publish only content already accepted by #61/#60. `GitHubCommitFile` values are publication material, not model mutation authority.
- `applied: true` or a provider `COMMIT_WRITTEN` result must never bypass #61's protected implementation validator.
- The branch/commit/PR path is publication after accepted implementation, not implementation generation.

## #46 — protected app-builder evaluation

Map only bounded safe evidence into #46 observation/evidence contracts:

- provider/tool/action identity;
- canonical Project/repository identity digest;
- source revision and accepted lineage digest;
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
