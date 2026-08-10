import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from app.config import settings
from app.data.loader import load_data
from app.schemas.answer import QuestionEnvelope, AnswerResponse
from app.schemas.agents import AgentRosterResponse
from app.agents.registry import get_agent_roster
from app.agents.router_agent import router_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s"
)
logger = logging.getLogger("valura")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Valura Multi-Agent Financial Service...")
    # Load client book and market data once at startup
    load_data()
    logger.info("✅ Data loaded and agents ready!")
    yield
    logger.info("👋 Shutting down Valura Service...")

app = FastAPI(
    title="Valura AI Financial Agent System",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "Valura AI Multi-Agent Q&A"}

@app.get("/agents", response_model=AgentRosterResponse, tags=["Agents"])
async def get_agents():
    return get_agent_roster()

@app.post("/answer", response_model=AnswerResponse, tags=["QA"])
async def answer_question(envelope: QuestionEnvelope):
    try:
        response = await router_agent.route_and_answer(envelope)
        return response
    except Exception as e:
        logger.error(f"Error processing question {envelope.question_id}: {e}", exc_info=True)
        # Fallback response for 100% availability compliance
        return AnswerResponse(
            question_id=envelope.question_id,
            client_id=envelope.client_id,
            answer_value=None,
            text="Unable to process question due to temporary service limitation.",
            abstained=True,
            refused=False,
            reason="service_error",
            citations=[envelope.client_id] if envelope.client_id else [],
            confidence=0.5,
            agents=["router"]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
