from app.schemas.agents import AgentInfo, AgentRosterResponse

ROSTER = [
    AgentInfo(
        name="RouterAgent",
        role="router",
        description="Classifies questions and dispatches to specialists."
    ),
    AgentInfo(
        name="BookQAAgent",
        role="book_qa",
        description="Answers questions on client positions, transactions, balances, and drift."
    ),
    AgentInfo(
        name="KYCProfileAgent",
        role="kyc_profile",
        description="Answers identity, KYC, risk, and employment queries with PII masking."
    ),
    AgentInfo(
        name="NotesDeskAgent",
        role="notes_desk",
        description="Processes free-text notes, advisor memos, and transaction notes."
    ),
    AgentInfo(
        name="MarketDeskAgent",
        role="market_desk",
        description="Provides market prices, instrument metadata, news, and coverage verification."
    ),
    AgentInfo(
        name="ComplianceAgent",
        role="compliance",
        description="Handles out-of-scope refusals, advice refusals, and coverage refusals."
    ),
]

def get_agent_roster() -> AgentRosterResponse:
    return AgentRosterResponse(agents=ROSTER)
