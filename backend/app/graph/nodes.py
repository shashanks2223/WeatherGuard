from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional

from backend.app.graph.state import WeatherGuardState
from backend.app.schemas.decision import Decision, DecisionStatus, EvidencePack
from backend.app.schemas.intent import UserIntent
from backend.app.schemas.policy import PolicyMatch
from backend.app.schemas.weather import WeatherSnapshot
from backend.app.services.llm_service import BaseLLMProvider, get_llm_provider
from backend.app.services.policy_engine import PolicyEngine
from backend.app.services.weather_service import (
    GeocodingError,
    OpenMeteoClient,
    WeatherServiceError,
)

logger = logging.getLogger(__name__)

class GraphNodes:
    """Encapsulates all node actions for the WeatherGuard LangGraph workflow."""

    def __init__(
        self,
        policy_engine: Optional[PolicyEngine] = None,
        weather_client: Optional[OpenMeteoClient] = None,
        llm_provider: Optional[BaseLLMProvider] = None,
    ):
        self.policy_engine = policy_engine or PolicyEngine()
        self.weather_client = weather_client or OpenMeteoClient()
        self.llm_provider = llm_provider or get_llm_provider()

    async def parse_intent_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Extracts structured intent from user query and retains multi-turn session context."""
        query = state.get("user_query", "")
        extracted = await self.llm_provider.extract_intent(query)

        # Context carry-over from previous turn in same session
        prev_intent = state.get("intent")
        prev_location = state.get("location")

        final_activity = extracted.activity
        final_category = extracted.category
        final_user_group = extracted.user_group
        final_location_query = extracted.location

        if prev_intent:
            # If current query doesn't specify activity (or is generic) but prior turn did, carry it forward
            if final_activity in ["general_outdoor", "general"] and prev_intent.activity not in ["general_outdoor", "general"]:
                final_activity = prev_intent.activity
                final_category = prev_intent.category

            # If user group was not specified in follow-up, inherit from previous turn
            has_explicit_group = any(
                marker in query.lower()
                for marker in ["child", "kid", "toddler", "daughter", "son", "baby", "infant", "elderly", "senior", "parent", "grandparent", "aged"]
            )
            if not has_explicit_group and prev_intent.user_group != final_user_group:
                final_user_group = prev_intent.user_group

        # If location wasn't specified in current query, check previous turn
        if not final_location_query and prev_location:
            final_location_query = prev_location.name
        elif not final_location_query and prev_intent and prev_intent.location:
            final_location_query = prev_intent.location

        merged_intent = UserIntent(
            activity=final_activity,
            category=final_category,
            location=final_location_query,
            time_scope=extracted.time_scope,
            user_group=final_user_group,
            confidence=extracted.confidence,
            raw_query=query,
        )

        logger.info(
            f"Intent Parsed: activity='{merged_intent.activity}', location='{merged_intent.location}', "
            f"time_scope='{merged_intent.time_scope}', user_group='{merged_intent.user_group}'"
        )

        return {
            "intent": merged_intent,
            "location_query": final_location_query,
            "error_message": None,
        }

    async def request_location_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Polite prompt when user does not provide a location."""
        return {
            "decision": Decision(
                status=DecisionStatus.LOCATION_REQUIRED,
                reasons=["User did not specify a city or location."],
            ),
            "response_text": (
                "Please specify the city or location you are inquiring about so I can "
                "retrieve local weather data and evaluate applicable safety policies."
            ),
        }

    async def resolve_location_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Resolves location query using Open-Meteo geocoding."""
        loc_query = state.get("location_query")
        if not loc_query:
            return {"error_message": "Missing location query"}

        try:
            resolved = await self.weather_client.resolve_location(loc_query)
            if not resolved:
                return {
                    "error_message": f"Could not find coordinates for location '{loc_query}'",
                    "location": None,
                }
            return {
                "location": resolved,
                "error_message": None,
            }
        except (GeocodingError, Exception) as exc:
            logger.error(f"Geocoding exception for '{loc_query}': {exc}")
            return {
                "error_message": f"Geocoding service failure: {str(exc)}",
                "location": None,
            }

    async def location_failure_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Honest failure when location lookup fails."""
        loc_str = state.get("location_query", "the requested location")
        return {
            "decision": Decision(
                status=DecisionStatus.LOCATION_ERROR,
                reasons=[f"Unable to geocode location '{loc_str}'."],
            ),
            "response_text": (
                f"I couldn't resolve the location '{loc_str}'. "
                "Please check the spelling or provide a recognized city name."
            ),
        }

    async def fetch_weather_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Fetches live weather from Open-Meteo for the resolved coordinates."""
        loc = state.get("location")
        if not loc:
            return {"error_message": "Location not resolved before weather fetch"}

        intent = state.get("intent")
        time_scope = intent.time_scope if intent else "current"

        try:
            snapshot = await self.weather_client.fetch_weather(
                latitude=loc.latitude,
                longitude=loc.longitude,
                time_scope=time_scope,
            )
            return {
                "weather": snapshot,
                "error_message": None,
            }
        except (WeatherServiceError, Exception) as exc:
            logger.error(f"Weather fetch failed: {exc}")
            return {
                "error_message": f"Weather API failure: {str(exc)}",
                "weather": None,
            }

    async def weather_failure_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Honest failure when weather API is unreachable."""
        return {
            "decision": Decision(
                status=DecisionStatus.WEATHER_ERROR,
                reasons=["Open-Meteo weather service is currently unreachable."],
            ),
            "response_text": (
                "I couldn't retrieve current weather data for that location, "
                "so I can't provide policy-backed weather guidance right now."
            ),
        }

    async def evaluate_policies_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Deterministic policy evaluation against WeatherSnapshot."""
        intent = state.get("intent")
        weather = state.get("weather")
        if not intent or not weather:
            return {"matched_policies": []}

        matches = self.policy_engine.match(intent, weather)
        logger.info(f"Evaluated policies: found {len(matches)} matches: {[m.policy_id for m in matches]}")
        return {
            "matched_policies": matches,
        }

    async def no_policy_response_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Controlled outcome when no policy triggers."""
        return {
            "decision": Decision(
                status=DecisionStatus.NO_POLICY,
                selected_policy_id=None,
                matched_policy_ids=[],
                reasons=["No externalized safety policy matched the requested activity under current weather conditions."],
            ),
            "response_text": (
                "I don't currently have a policy that covers this activity under the available conditions, "
                "so I can't provide policy-backed weather guidance for it."
            ),
        }

    async def resolve_policy_conflict_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Deterministically selects the winning policy according to severity, priority, and specificity."""
        matches: List[PolicyMatch] = state.get("matched_policies", [])
        winner = self.policy_engine.resolve_conflicts(matches)

        if not winner:
            return {
                "selected_policy": None,
                "decision": Decision(status=DecisionStatus.NO_POLICY),
            }

        other_policy_reasons = [
            f"{match.policy_id} did not win: severity={match.severity.value}, priority={match.priority}, specificity={len(match.evaluated_reasons)}"
            for match in matches
            if match.policy_id != winner.policy_id
        ]
        selection_reason = (
            "Selected by severity, then priority, specificity, and stable policy ID tie-breaker."
        )
        if other_policy_reasons:
            selection_reason += " " + " ".join(other_policy_reasons)

        decision = Decision(
            status=DecisionStatus.MATCHED,
            selected_policy_id=winner.policy_id,
            selected_policy=winner.policy_obj,
            severity=winner.severity,
            matched_policies=matches,
            matched_policy_ids=[m.policy_id for m in matches],
            reasons=winner.evaluated_reasons,
            selection_reason=selection_reason,
        )

        return {
            "selected_policy": winner,
            "decision": decision,
        }

    async def build_evidence_pack_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Assembles immutable-style EvidencePack."""
        selected: Optional[PolicyMatch] = state.get("selected_policy")
        evidence = EvidencePack(
            intent=state["intent"],
            location=state.get("location"),
            weather=state.get("weather"),
                    matched_policies=state.get("matched_policies", []),
            selected_policy=selected.policy_obj if selected else None,
            severity=selected.severity if selected else None,
            matched_conditions=selected.evaluated_reasons if selected else [],
            evidence_fields=selected.policy_obj.evidence_fields if selected else [],
            selection_reason=(
                state.get("decision").selection_reason
                if state.get("decision") else None
            ),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return {
            "evidence_pack": evidence,
        }

    async def compose_response_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Constrained LLM response composition strictly bounded by EvidencePack."""
        evidence: Optional[EvidencePack] = state.get("evidence_pack")
        if not evidence:
            return {"response_text": "Error: Evidence pack is missing."}

        text = await self.llm_provider.compose_response(evidence)
        return {
            "response_text": text,
        }

    async def validate_response_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Deterministic safety auditor. Verifies policy and weather grounding."""
        response_text = state.get("response_text", "")
        selected: Optional[PolicyMatch] = state.get("selected_policy")
        weather: Optional[WeatherSnapshot] = state.get("weather")
        evidence: Optional[EvidencePack] = state.get("evidence_pack")

        is_valid = True
        validation_errors = []

        if selected:
            # 1. Selected policy ID must appear in response
            if selected.policy_id not in response_text:
                is_valid = False
                validation_errors.append(f"Missing required policy ID {selected.policy_id} in response")

            # 2. Response must not cite unselected policy IDs
            other_ids = [p.id for p in self.policy_engine.policies if p.id != selected.policy_id]
            for pid in other_ids:
                if re.search(rf"\b{re.escape(pid)}\b", response_text):
                    is_valid = False
                    validation_errors.append(f"Hallucinated unselected policy ID {pid} in response")

            expected_severity = selected.severity.value.capitalize()
            if expected_severity not in response_text:
                is_valid = False
                validation_errors.append("Response severity is missing or changed")

            if weather:
                for value in (weather.temperature_c, weather.wind_speed_kmh, weather.precipitation_mm):
                    if str(value) not in response_text:
                        is_valid = False
                        validation_errors.append(f"Weather value {value} is not grounded in response")
                if weather.precipitation_probability is not None and str(weather.precipitation_probability) not in response_text:
                    is_valid = False
                    validation_errors.append("Precipitation probability is not grounded in response")
                if weather.uv_index is not None and str(weather.uv_index) not in response_text:
                    is_valid = False
                    validation_errors.append("UV index is not grounded in response")
        elif state.get("decision", {}).status == DecisionStatus.NO_POLICY:
            if any(term in response_text.lower() for term in ["avoid", "safe", "danger", "recommend"]):
                is_valid = False
                validation_errors.append("No-policy response contains unsupported safety advice")

        if not is_valid:
            logger.warning("Response validation failed: %s", validation_errors)
            if evidence:
                from backend.app.services.llm_service import MockLLMProvider
                response_text = await MockLLMProvider().compose_response(evidence)

        # Update history
        history = state.get("history", [])
        new_history = list(history)
        new_history.append({"role": "user", "content": state.get("user_query", "")})
        new_history.append({"role": "assistant", "content": response_text})

        return {
            "response_text": response_text,
            "validation_passed": is_valid,
            "validation_errors": validation_errors,
            "history": new_history,
        }

    async def deterministic_fallback_node(self, state: WeatherGuardState) -> Dict[str, Any]:
        """Generate a response only from trusted EvidencePack data after validation fails."""
        evidence: Optional[EvidencePack] = state.get("evidence_pack")
        if not evidence:
            return {"response_text": "I could not validate a policy-backed response.", "validation_passed": False}
        from backend.app.services.llm_service import MockLLMProvider
        response = await MockLLMProvider().compose_response(evidence)
        return {"response_text": response, "validation_passed": False}
