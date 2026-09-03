from pathlib import Path

path = Path("ARCHITECTURE.md")
text = path.read_text()
old_version = "Version: 3.50"
if text.count(old_version) != 1:
    raise SystemExit(f"expected one architecture version anchor, found {text.count(old_version)}")
text = text.replace(old_version, "Version: 3.51", 1)
anchor = "Architecture v3.50 adds an explicit bounded human correction loop"
if text.count(anchor) != 1:
    raise SystemExit(f"expected one v3.50 anchor, found {text.count(anchor)}")
paragraph = (
    "Architecture v3.51 distinguishes provider repository emptiness from an ordinary commit-bearing default branch whose exact head tree is the universal canonical Git empty tree. For a durable greenfield-root Engineering Run at REVIEW, delivery now performs a server-owned read-only exact-repository inspection before choosing its publication base: a truly empty repository with no usable default head still requires the deterministic two-commit Parallax initializer; an exact Parallax cleanup-looking head still requires the complete actor/message/parent/bootstrap-marker/blob/provenance/default-ref baseline proof; an ordinary commit-bearing head whose exact tree SHA is `4b825dc642cb6eb9a060e54bf8d69288fbee4904` may be used directly as the bounded feature-branch base without rewriting or initializing the default branch; and any commit-bearing non-empty drift fails closed before branch/commit/PR mutation. Commit-bearing inspection reads the exact default ref, exact head commit and tree identity and then re-reads the default ref, so concurrent movement fails before publication. The existing exact accepted same-run lineage remains the only application source authority, and downstream feature branch, lineage commit, pull request, Vercel Preview, delivery-record replay and human REVIEW boundaries are unchanged. Repository inspection reuses the existing exact-repository read authority; no provider permission, credential, force-ref, default-branch application publication, merge, production-promotion or automatic REVIEW authority is added. Architecture v3.50 remains the bounded REVIEW-rework foundation.\n\n"
)
text = text.replace(anchor, paragraph + anchor, 1)
path.write_text(text)
