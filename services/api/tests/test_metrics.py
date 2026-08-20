from parallax_api.intelligence.protected_metrics import evaluate_reasoning_output, evaluate_spec_contract


def test_protected_spec_metric_rejects_missing_contract():
    result = evaluate_spec_contract("# incomplete")
    assert not result.passed
    assert result.score < 1


def test_reasoning_metric_accepts_normal_answer():
    result = evaluate_reasoning_output("This answer is long enough to satisfy the protected minimum contract.")
    assert result.passed
