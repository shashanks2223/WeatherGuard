import pytest

from evals.evaluator import WeatherGuardEvaluator


@pytest.mark.asyncio
async def test_deterministic_evaluation_cases_are_green() -> None:
    evaluator = WeatherGuardEvaluator()
    cases = [
        evaluator.eval_01_clear_sop_match,
        evaluator.eval_02_second_sop_match,
        evaluator.eval_03_paraphrase,
        evaluator.eval_04_second_paraphrase,
        evaluator.eval_07_deterministic_severe_weather,
        evaluator.eval_08_no_policy,
        evaluator.eval_09_weather_failure,
        evaluator.eval_10_geocoding_failure,
        evaluator.eval_11_prompt_injection,
        evaluator.eval_12_fake_policy_injection,
        evaluator.eval_13_session_memory,
        evaluator.eval_14_multiple_policy_match,
        evaluator.eval_15_routine_conditions,
        evaluator.eval_16_policy_boundary,
        evaluator.eval_17_response_grounding,
        evaluator.eval_18_policy_hot_reload,
        evaluator.eval_19_policy_file_integrity,
        evaluator.eval_20_adversarial_weather_claim,
    ]

    results = [await case() for case in cases]
    assert all(result.status == "PASS" for result in results), [
        (result.test_id, result.status, result.explanation)
        for result in results
        if result.status != "PASS"
    ]


@pytest.mark.asyncio
async def test_live_severe_case_is_honest_about_applicability() -> None:
    result = await WeatherGuardEvaluator().eval_06_live_severe_weather()
    assert result.status in {"PASS", "NOT_APPLICABLE"}
    assert result.status != "FAIL"
