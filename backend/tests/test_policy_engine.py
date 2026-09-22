import pytest
from backend.app.schemas.intent import CategoryEnum, UserGroupEnum, UserIntent
from backend.app.schemas.policy import SeverityLevel
from backend.app.schemas.weather import WeatherSnapshot
from backend.app.services.policy_engine import PolicyEngine

def test_load_all_policies(policy_engine: PolicyEngine):
    assert len(policy_engine.policies) >= 12
    categories = {p.category for p in policy_engine.policies}
    assert "outdoor_exercise" in categories
    assert "travel" in categories
    assert "vulnerable_groups" in categories
    assert "recreation" in categories

def test_single_condition_match(policy_engine: PolicyEngine, high_wind_weather: WeatherSnapshot):
    intent = UserIntent(
        activity="cycling",
        category=CategoryEnum.OUTDOOR_EXERCISE,
        user_group=UserGroupEnum.ADULT,
        time_scope="today"
    )
    matches = policy_engine.match(intent, high_wind_weather)
    matched_ids = [m.policy_id for m in matches]
    assert "EX-WIND-01" in matched_ids
    win = policy_engine.resolve_conflicts(matches)
    assert win is not None
    assert win.policy_id == "EX-WIND-01"
    assert win.severity == SeverityLevel.HIGH

def test_vulnerable_group_matching(policy_engine: PolicyEngine):
    # Elderly walking in high heat (34C)
    heat_weather = WeatherSnapshot(
        timestamp="2026-09-22T14:00:00Z",
        temperature_c=34.0,
        wind_speed_kmh=10.0,
        precipitation_mm=0.0
    )
    # Elderly query should match VG-ELDER-HEAT-01
    elderly_intent = UserIntent(
        activity="walking",
        category=CategoryEnum.VULNERABLE_GROUPS,
        user_group=UserGroupEnum.ELDERLY
    )
    matches = policy_engine.match(elderly_intent, heat_weather)
    assert any(m.policy_id == "VG-ELDER-HEAT-01" for m in matches)

    # General adult walk under 34C should NOT match the geriatric policy
    adult_intent = UserIntent(
        activity="walking",
        category=CategoryEnum.OUTDOOR_EXERCISE,
        user_group=UserGroupEnum.ADULT
    )
    matches_adult = policy_engine.match(adult_intent, heat_weather)
    assert not any(m.policy_id == "VG-ELDER-HEAT-01" for m in matches_adult)

def test_fuzzy_composite_profile(policy_engine: PolicyEngine):
    # Picnic with 2 violations: rain prob 45% and wind 30 km/h
    picnic_weather = WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=22.0,
        wind_speed_kmh=30.0,
        precipitation_mm=0.0,
        precipitation_probability=45,
        uv_index=5.0
    )
    intent = UserIntent(
        activity="picnic",
        category=CategoryEnum.RECREATION,
        user_group=UserGroupEnum.ADULT
    )
    matches = policy_engine.match(intent, picnic_weather)
    assert any(m.policy_id == "RC-OUTING-PROFILE-01" for m in matches)

def test_multiple_match_conflict_resolution(policy_engine: PolicyEngine, storm_weather: WeatherSnapshot):
    # Commuting in storm has both gale wind (TR-GALE-01, High, priority 82)
    # and severe downpour (TR-STORM-01, Critical, priority 95)
    intent = UserIntent(
        activity="commuting",
        category=CategoryEnum.TRAVEL,
        user_group=UserGroupEnum.ADULT
    )
    matches = policy_engine.match(intent, storm_weather)
    matched_ids = [m.policy_id for m in matches]
    assert len(matched_ids) >= 2
    assert "TR-STORM-01" in matched_ids

    # Critical severity + Priority 95 should win over High / 82
    winner = policy_engine.resolve_conflicts(matches)
    assert winner is not None
    assert winner.policy_id == "TR-STORM-01"
    assert winner.severity == SeverityLevel.CRITICAL

def test_routine_cycling_policy_matches_normal_conditions(policy_engine: PolicyEngine):
    intent = UserIntent(
        activity="cycling",
        category=CategoryEnum.OUTDOOR_EXERCISE,
        user_group=UserGroupEnum.ADULT
    )
    normal_weather = WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=27.9,
        wind_speed_kmh=15.6,
        precipitation_mm=0.0,
        precipitation_probability=1,
        uv_index=5.7,
    )
    matches = policy_engine.match(intent, normal_weather)
    routine = next(match for match in matches if match.policy_id == "EX-CYCLE-ROUTINE-01")
    assert routine.severity == SeverityLevel.LOW
    assert any("wind_speed_kmh (15.6) <= 34.0: MET" in reason for reason in routine.evaluated_reasons)
    assert any("temperature_c (27.9) between 8.0: MET" in reason for reason in routine.evaluated_reasons)


def test_routine_policy_loses_to_severe_wind(policy_engine: PolicyEngine):
    intent = UserIntent(activity="cycling", category=CategoryEnum.OUTDOOR_EXERCISE, user_group=UserGroupEnum.ADULT)
    severe_weather = WeatherSnapshot(
        timestamp="2026-09-22T12:00:00Z",
        temperature_c=27.0,
        wind_speed_kmh=45.0,
        precipitation_mm=0.0,
        precipitation_probability=1,
        uv_index=5.0,
    )
    matches = policy_engine.match(intent, severe_weather)
    assert "EX-CYCLE-ROUTINE-01" not in [match.policy_id for match in matches]
    assert policy_engine.resolve_conflicts(matches).policy_id == "EX-WIND-01"


def test_unsupported_drone_activity_remains_no_policy(policy_engine: PolicyEngine, benign_weather: WeatherSnapshot):
    intent = UserIntent(activity="drone_flying", category=CategoryEnum.GENERAL, user_group=UserGroupEnum.ADULT)
    assert policy_engine.match(intent, benign_weather) == []
