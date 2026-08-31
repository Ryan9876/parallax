from pathlib import Path

path = Path("ARCHITECTURE.md")
text = path.read_text()
if not text.startswith("# Parallax 2.0 Architecture\n\nVersion: 3.38\nStatus: Authoritative\n\n## Version relationship\n\n"):
    raise SystemExit("architecture version seam does not match v3.38")
text = text.replace("Version: 3.38", "Version: 3.39", 1)
marker = "## Version relationship\n\n"
paragraph = (
    "Architecture v3.39 extends v3.38 incremental IMPLEMENT convergence across work-unit boundaries without widening model, retry, timeout, or mutation authority. Before a locally converged work unit is completed, the resilient live controller now preflights its canonical patches together with the already completed non-authoritative plan prefix through the same server-owned `ProposalSafetyPreflight` / `SafeImplementationEngine` boundary. A plan-prefix rejection keeps only the current work unit inside the existing finite distinct-agent recovery and single final validator-repair loop; already completed work-unit intent remains unchanged, current-generation additions are not retained, and repair guidance receives only bounded target names plus fixed sanitized reason codes. The final exact-acceptance and whole-plan safe preflight remains mandatory defense in depth before disposable BUILD/TEST/VERIFY and independent evaluation. Architecture v3.39 also admits the existing server-owned `candidate_generation_failure` envelope into durable failed IMPLEMENT evidence only through a closed bounded sanitizer: fixed reason vocabularies, bounded counts/generations and false authority claims may survive, while unknown fields, raw source/generated content, unified diffs, exception text, provider payloads, credentials, environment values and true mutation/lineage/Git/deployment/REVIEW claims are dropped. Luna/Terra/Sol routing, the 60-second hosted timeout, zero hidden provider retries, candidate reassignment ceiling, single validator repair, request autonomy budget, source-lineage authority, Git/deployment authority, lifecycle authority and human REVIEW ceiling are unchanged. Architecture v3.38 remains the per-file and per-work-unit incremental convergence foundation.\n\n"
if text.count(marker) != 1:
    raise SystemExit("architecture version-relationship seam is not unique")
text = text.replace(marker, marker + paragraph, 1)
path.write_text(text)
