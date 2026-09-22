import logging
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.graph.graph import create_weatherguard_graph
from backend.app.graph.nodes import GraphNodes
from backend.app.schemas.decision import ChatRequest, ChatResponse
from backend.app.services.policy_engine import PolicyEngine

app = FastAPI(
    title="WeatherGuard API",
    description="Policy-first weather advisory API",
    version="1.0.0",
)

logger = logging.getLogger("weatherguard.api")
policy_engine = PolicyEngine(policies_dir=settings.POLICIES_DIR)
graph = create_weatherguard_graph(GraphNodes(policy_engine=policy_engine))
allowed_origins = list(dict.fromkeys(
    origin for origin in settings.CORS_ORIGINS + [settings.FRONTEND_URL] if origin
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.get("/api/health", tags=["Monitoring"])
async def health_check():
    """Return a lightweight readiness response."""
    return {
        "status": "ok",
        "service": "weatherguard-api",
        "llm_provider": settings.LLM_PROVIDER,
        "policies_loaded": len(policy_engine.policies),
        "version": "1.0.0",
    }


@app.get("/api/policies", tags=["Policies"])
async def list_policies():
    return [
        {
            **policy.model_dump(exclude={"conditions"}),
            "recommendation": policy.guidance.recommendation,
        }
        for policy in policy_engine.policies
    ]


@app.post("/api/policies/reload", tags=["Policies"])
async def reload_policies():
    count = policy_engine.reload_policies()
    return {"status": "ok", "policies_count": count}


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or str(uuid.uuid4())
    logger.info("Processing chat request for session %s", session_id)
    try:
        result = await graph.ainvoke(
            {
                "session_id": session_id,
                "user_query": request.message,
                "history": [],
            },
            config={"configurable": {"thread_id": session_id}},
        )
        return ChatResponse(
            session_id=session_id,
            response=result.get("response_text", ""),
            decision=result.get("decision"),
            evidence=result.get("evidence_pack"),
            validation_passed=result.get("validation_passed", True),
        )
    except Exception as exc:
        logger.exception("Chat request failed for session %s", session_id)
        raise HTTPException(status_code=500, detail="Unable to process weather advisory request") from exc
