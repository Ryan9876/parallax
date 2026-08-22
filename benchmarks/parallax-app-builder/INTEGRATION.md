# App-builder evaluation integration notes

This benchmark slice is intentionally provider-neutral and additive. It evaluates observable project/spec/run bindings, result identities, authorization decisions, and evidence digests without importing the unmerged implementation contracts from the parallel Wave 1 workers.

## Future interface mapping

- **#43 Project/App lifecycle:** map the accepted durable Project ID to `project_ref` and the accepted isolated workspace identity to `workspace_ref`. A mismatch remains a critical evaluation failure; do not weaken the benchmark to accommodate a competing identifier.
- **#44 Safe implementation/patch engine:** map accepted patch/application evidence and inspectable before/after or diff digests into `evidence_digests` plus bounded observation tokens such as `implementation.patch=bounded` and `diff.inspectable=true`. Prose-only implementation claims remain forbidden.
- **#45 Tool authority:** map the accepted capability/action audit decision into bounded observations for decision and reason identity. No provider credential, raw request payload, shell command, or hidden reasoning belongs in benchmark evidence.

## Serialized integration work

Integration / Control Tower should adapt the producer-to-observation mapping only after #43/#44/#45 interfaces are accepted. It may then wire app-builder promotion evaluation into CI above optimization, preserving development/promotion separation and existing Engineering/Reason/Code protected thresholds.

This workstream does not authorize merge, deployment, threshold changes, or production promotion.
