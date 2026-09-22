import logging
from typing import Literal, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from backend.app.graph.nodes import GraphNodes
from backend.app.graph.state import WeatherGuardState

logger = logging.getLogger(__name__)

def route_check_location(state: WeatherGuardState) -> Literal["missing", "available"]:
    """Conditional router: checks if location query is present."""
    loc = state.get("location_query")
    if not loc or not str(loc).strip():
        return "missing"
    return "available"

def route_check_location_resolution(state: WeatherGuardState) -> Literal["failed", "success"]:
    """Conditional router: checks if geocoding succeeded."""
    if state.get("error_message") or not state.get("location"):
        return "failed"
    return "success"

def route_check_weather(state: WeatherGuardState) -> Literal["failed", "success"]:
    """Conditional router: checks if weather fetching succeeded."""
    if state.get("error_message") or not state.get("weather"):
        return "failed"
    return "success"

def route_check_policy_match(state: WeatherGuardState) -> Literal["no_match", "matched"]:
    """Conditional router: checks if any SOP conditions matched."""
    matched = state.get("matched_policies", [])
    if not matched:
        return "no_match"
    return "matched"

def route_check_validation(state: WeatherGuardState) -> Literal["failure", "success"]:
    return "success" if state.get("validation_passed", False) else "failure"

def route_after_evidence(state: WeatherGuardState) -> Literal["compose", "end"]:
    decision = state.get("decision")
    return "compose" if decision and decision.status == "MATCHED" else "end"

def create_weatherguard_graph(nodes: Optional[GraphNodes] = None):
    """Builds and compiles the full WeatherGuard LangGraph with real conditional branches and session memory."""
    if nodes is None:
        nodes = GraphNodes()

    workflow = StateGraph(WeatherGuardState)

    # Add all nodes
    workflow.add_node("parse_intent", nodes.parse_intent_node)
    workflow.add_node("request_location", nodes.request_location_node)
    workflow.add_node("resolve_location", nodes.resolve_location_node)
    workflow.add_node("location_failure", nodes.location_failure_node)
    workflow.add_node("fetch_weather", nodes.fetch_weather_node)
    workflow.add_node("weather_failure", nodes.weather_failure_node)
    workflow.add_node("evaluate_policies", nodes.evaluate_policies_node)
    workflow.add_node("no_policy_response", nodes.no_policy_response_node)
    workflow.add_node("resolve_policy_conflict", nodes.resolve_policy_conflict_node)
    workflow.add_node("build_evidence_pack", nodes.build_evidence_pack_node)
    workflow.add_node("compose_response", nodes.compose_response_node)
    workflow.add_node("validate_response", nodes.validate_response_node)
    workflow.add_node("deterministic_fallback", nodes.deterministic_fallback_node)

    # Wire Edges
    workflow.add_edge(START, "parse_intent")

    # Branch 1: Location Check
    workflow.add_conditional_edges(
        "parse_intent",
        route_check_location,
        {
            "missing": "request_location",
            "available": "resolve_location",
        }
    )
    workflow.add_edge("request_location", "build_evidence_pack")

    # Branch 2: Location Resolution Check
    workflow.add_conditional_edges(
        "resolve_location",
        route_check_location_resolution,
        {
            "failed": "location_failure",
            "success": "fetch_weather",
        }
    )
    workflow.add_edge("location_failure", "build_evidence_pack")

    # Branch 3: Weather Fetch Check
    workflow.add_conditional_edges(
        "fetch_weather",
        route_check_weather,
        {
            "failed": "weather_failure",
            "success": "evaluate_policies",
        }
    )
    workflow.add_edge("weather_failure", "build_evidence_pack")

    # Branch 4: Policy Match Check
    workflow.add_conditional_edges(
        "evaluate_policies",
        route_check_policy_match,
        {
            "no_match": "no_policy_response",
            "matched": "resolve_policy_conflict",
        }
    )
    workflow.add_edge("no_policy_response", "build_evidence_pack")

    # Sequential flow for matched policy
    workflow.add_edge("resolve_policy_conflict", "build_evidence_pack")
    workflow.add_conditional_edges(
        "build_evidence_pack",
        route_after_evidence,
        {"compose": "compose_response", "end": END},
    )
    workflow.add_edge("compose_response", "validate_response")
    workflow.add_conditional_edges(
        "validate_response",
        route_check_validation,
        {"failure": "deterministic_fallback", "success": END},
    )
    workflow.add_edge("deterministic_fallback", END)

    # Compile with in-memory checkpointer for session state
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled graph instance for the application
weatherguard_app = create_weatherguard_graph()
