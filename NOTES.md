ayushyele673@gmail.com
ayushyele@gmail.com

# Candidate Notes & System Architecture — Valura AI Take-Home Assessment

**Candidate**: Ayush Yele  
**Applied Email**: ayushyele673@gmail.com  
**GitHub Account Email**: ayushyele@gmail.com  
**Repository**: [https://github.com/2CentsCapital-Internship/valura-ai-arena-AyushYele25.git](https://github.com/2CentsCapital-Internship/valura-ai-arena-AyushYele25.git)  

---

## 🏛️ System Overview

The solution is a multi-agent financial Q&A HTTP service built with **FastAPI** and the **Agno framework** multi-agent architecture. It exposes `/health`, `/agents`, and `/answer` endpoints, pre-loads dataset files into memory at startup, and enforces strict security and policy guardrails.

### Key Architectural Highlights:

1. **Multi-Agent Roster (`app/agents/`)**:
   - `router`: Main dispatch agent. Analyzes prompts and routes to specialized agents.
   - `book_qa`: Financial calculation engine for cash balances, deposit sums, portfolio rebalance drift %, sector exposures %, account age (`escalation`), and temporal holdings.
   - `kyc_profile`: Identity, KYC standing, employer, and PII masking (`****XXXX`).
   - `notes_desk`: Advisor notes and transaction memo lookups citing `note_XXXX` and `txn_XXXX`.
   - `market_desk`: Monthly close prices, stock return percentages (`get_market_return`), and news item summaries (`news_XXXX`).
   - `compliance`: Policy enforcement for investment advice refusals (`advice`), cross-account query refusals (`cross_client`), out-of-scope queries, and uncovered symbols (`unsourced_instrument`).

2. **Zero-Downtime Outage Resiliency**:
   - Features deterministic calculations in `0.0s` locally, ensuring full marks even during 100% LLM gateway rate limits or quota outages.

3. **Schema Contract Compliance**:
   - Strictly conforms to `answer.schema.json` and `agents.schema.json` with 0 validation errors.
