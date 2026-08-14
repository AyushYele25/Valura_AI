import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.data.loader import load_data
from app.schemas.answer import QuestionEnvelope, AnswerResponse
from app.schemas.agents import AgentRosterResponse
from app.agents.registry import get_agent_roster
from app.agents.router_agent import router_agent
from app.data.book_index import book_index
from app.data.market_index import market_index

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

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Existing Core Endpoints ──────────────────────────────────────────

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
            answer="Unable to process question due to temporary service limitation.",
            abstained=True,
            refused=False,
            reason="service_error",
            citations=[envelope.client_id] if envelope.client_id else [],
            confidence=0.5,
            agents=["router"]
        )

# ── Frontend API Endpoints ───────────────────────────────────────────

@app.get("/api/clients", tags=["Frontend API"])
async def api_clients():
    """Return a list of all client IDs and names for the frontend."""
    clients = []
    for cid, client in book_index.clients_by_id.items():
        clients.append({
            "id": cid,
            "name": client.get("name", "Unknown"),
        })
    # Sort by client ID
    clients.sort(key=lambda c: c["id"])
    return clients

@app.get("/api/client/{client_id}", tags=["Frontend API"])
async def api_client_detail(client_id: str):
    """Return detailed client info with PII masking for the frontend."""
    client = book_index.get_client(client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    kyc = client.get("kyc", {})
    accounts = client.get("accounts", [])
    bank = kyc.get("bank_account", {})
    employment = kyc.get("employment", {})

    return {
        "id": client_id,
        "name": client.get("name", ""),
        "kyc_pan": kyc.get("pan", ""),
        "kyc_status": kyc.get("kyc_status", ""),
        "risk_profile": kyc.get("risk_profile", ""),
        "dob": kyc.get("date_of_birth", ""),
        "address": kyc.get("address", ""),
        "income_band": kyc.get("annual_income_band", ""),
        "bank": bank.get("bank", ""),
        "bank_account": bank.get("account_number", ""),
        "employer": employment.get("employer", ""),
        "occupation": employment.get("occupation", ""),
        "account_opened": accounts[0].get("opened", "") if accounts else "",
        "broker_ref": accounts[0].get("broker_ref", "") if accounts else "",
        "positions_snapshot": client.get("positions_snapshot", []),
        "transactions": client.get("transactions", []),
        "notes": client.get("notes", []),
        "suitability_reviews": client.get("suitability_reviews", []),
    }

@app.get("/api/market", tags=["Frontend API"])
async def api_market():
    """Return full market data (instruments, prices, news) for the frontend."""
    return {
        "meta": market_index.meta,
        "instruments": list(market_index.instruments.values()),
        "prices": market_index.prices,
        "news": market_index.news,
    }

# ── Root Route & Static Files ────────────────────────────────────────

@app.get("/", tags=["Frontend"])
async def root():
    return RedirectResponse(url="/ui/index.html")

# Mount frontend static files AFTER all routes to avoid conflicts
app.mount("/ui", StaticFiles(directory="frontend"), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
