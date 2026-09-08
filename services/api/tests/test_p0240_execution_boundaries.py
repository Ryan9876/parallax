from __future__ import annotations

from hashlib import sha256

from parallax_api.code.cache import BoundedDerivedCache, DerivedCacheKey
from parallax_api.code.implementation import ImplementationRequest, SafeImplementationEngine
from parallax_api.code.patching import SourcePatch


def test_derived_cache_identity_is_deterministic_ttl_bounded_and_non_authoritative() -> None:
    now = [10.0]
    cache: BoundedDerivedCache[str] = BoundedDerivedCache(
        ttl_seconds=5,
        max_entries=2,
        clock=lambda: now[0],
    )
    first = DerivedCacheKey.build("p0240.test", {"run": "r1", "revision": 2, "flag": True})
    same = DerivedCacheKey.build("p0240.test", {"flag": True, "revision": 2, "run": "r1"})
    other = DerivedCacheKey.build("p0240.test", {"run": "r2", "revision": 2, "flag": True})
    third = DerivedCacheKey.build("p0240.test", {"run": "r3", "revision": 2, "flag": True})
    assert first == same

    calls = 0

    def compute() -> str:
        nonlocal calls
        calls += 1
        return "derived-only"

    value, hit = cache.get_or_compute(first, compute)
    assert (value, hit, calls) == ("derived-only", False, 1)
    value, hit = cache.get_or_compute(same, compute)
    assert (value, hit, calls) == ("derived-only", True, 1)

    cache.put(other, "other")
    cache.put(third, "third")
    assert len(cache) == 2
    assert cache.get(first) is None  # LRU eviction, not durable authority.

    now[0] += 6
    assert cache.get(other) is None


def test_implementation_prepare_is_pure_and_apply_remains_the_only_mutation_boundary(tmp_path) -> None:
    target = tmp_path / "app.py"
    target.write_text("value = 1\n", encoding="utf-8")
    before = target.read_bytes()
    patch = SourcePatch(
        path="app.py",
        expected_base_sha256=sha256(before).hexdigest(),
        unified_diff=(
            "--- a/app.py\n"
            "+++ b/app.py\n"
            "@@ -1 +1 @@\n"
            "-value = 1\n"
            "+value = 2\n"
        ),
    )
    request = ImplementationRequest(patches=(patch,))
    engine = SafeImplementationEngine()

    plan = engine.prepare(tmp_path, request)
    assert target.read_text(encoding="utf-8") == "value = 1\n"
    assert len(plan.patches) == 1
    assert plan.total_source_bytes == len(before)
    assert plan.total_patch_bytes > 0
    assert plan.total_result_bytes == len(b"value = 2\n")

    evidence = engine.apply(tmp_path, request)
    assert target.read_text(encoding="utf-8") == "value = 2\n"
    assert evidence["applied"] is True
    assert evidence["protected_stage_authority"] is False
    assert evidence["git_mutation"] is False
    assert evidence["deployment_mutation"] is False
