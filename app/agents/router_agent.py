import logging
import re
from typing import List
from app.schemas.answer import QuestionEnvelope, AnswerResponse
from app.data.book_index import book_index
from app.data.market_index import market_index
from app.agents.compliance_agent import compliance_agent
from app.agents.book_qa_agent import book_qa_agent
from app.agents.kyc_profile_agent import kyc_profile_agent
from app.agents.notes_desk_agent import notes_desk_agent
from app.agents.market_desk_agent import market_desk_agent

logger = logging.getLogger(__name__)

class RouterAgent:
    def extract_symbols(self, text: str) -> List[str]:
        candidates = re.findall(r'\b[A-Z]{2,10}\b', text)
        ignored = {"USD", "INR", "KYC", "PAN", "IFSC", "LRS", "T+1", "API", "CPU", "RAM", "POST", "GET", "WHAT", "HOW", "WHEN", "WHERE", "WHY", "IS", "ARE", "FOR", "THE", "AND"}
        return [c for c in candidates if c not in ignored]

    async def route_and_answer(self, envelope: QuestionEnvelope) -> AnswerResponse:
        qid = envelope.question_id
        cid = envelope.client_id
        prompt = envelope.prompt

        agent_roles = ["router"]

        # Check client validity
        is_client_valid = True
        if cid:
            is_client_valid = book_index.get_client(cid) is not None

        symbols = self.extract_symbols(prompt)
        prompt_lower = prompt.lower()

        # 1. Unanswerable check (email, mobile number, nominee, passport, venue)
        unanswerable_keywords = ["email address", "mobile number", "phone number", "nominee", "social security", "passport", "execution venue", "clearing firm"]
        if any(kw in prompt_lower for kw in unanswerable_keywords):
            agent_roles.append("kyc_profile")
            return AnswerResponse(
                question_id=qid,
                client_id=cid,
                answer="Information not present in client record.",
                answer_value=None,
                abstained=True,
                refused=False,
                reason="unanswerable",
                citations=[],
                confidence=1.0,
                agents=agent_roles
            )

        # 1b. Out-of-scope general-knowledge detection
        financial_keywords = [
            "cash", "balance", "position", "holding", "portfolio", "transaction",
            "deposit", "fee", "drift", "allocation", "quantity", "share", "shares",
            "bought", "sold", "dividend", "price", "sector", "industry", "news",
            "headline", "stock", "close", "kyc", "pan", "dob", "birth",
            "income", "bank", "ifsc", "address", "risk", "employment", "employer",
            "note", "memo", "advisor", "review", "interaction", "discussion",
            "account", "client", "market", "instrument", "symbol", "trade",
            "buy", "sell", "invest", "rebalance", "weight", "mandate",
            "funding", "withdrawal", "settle", "settlement", "purchase",
            "disposal", "suitability", "compliance", "broker", "demat",
            "overweight", "underweight", "concentrated", "proportion",
            "how many", "how much", "total", "largest", "biggest", "first",
            "latest", "recent", "current", "open", "days"
        ]
        has_financial_context = any(kw in prompt_lower for kw in financial_keywords)
        has_client_ref = bool(cid) or bool(re.search(r'\bcli_\d{4}\b', prompt))
        has_symbol_ref = bool(symbols)

        if not has_financial_context and not has_client_ref and not has_symbol_ref:
            agent_roles.append("compliance")
            return AnswerResponse(
                question_id=qid,
                client_id=cid,
                answer="This question is outside the scope of our financial advisory service. I can only answer questions about client accounts, positions, transactions, KYC profiles, and covered market instruments.",
                answer_value=None,
                abstained=False,
                refused=True,
                reason="out_of_scope_topic",
                citations=[],
                confidence=1.0,
                agents=agent_roles
            )

        # 2. Compliance Refusal Check
        is_refusal, reason_text, cat = compliance_agent.check_refusal(
            prompt=prompt,
            client_id=cid,
            is_client_valid=is_client_valid,
            mentioned_symbols=symbols,
            covered_symbols=market_index.covered_symbols
        )

        if is_refusal:
            agent_roles.append("compliance")
            return AnswerResponse(
                question_id=qid,
                client_id=cid,
                answer=reason_text,
                answer_value=None,
                abstained=False,
                refused=True,
                reason=cat,
                citations=[],
                confidence=1.0,
                agents=agent_roles
            )

        # 2b. Unsourced instrument check (abstain, not refuse)
        if symbols and not any(kw in prompt_lower for kw in ["hold", "share", "position", "cash", "balance", "transaction", "deposit", "dividend", "drift", "allocation", "fee", "bought", "purchase", "sell", "disposal"]):
            uncovered = [s for s in symbols if s not in market_index.covered_symbols]
            if uncovered:
                agent_roles.append("market_desk")
                return AnswerResponse(
                    question_id=qid,
                    client_id=cid,
                    answer=f"The symbol '{uncovered[0]}' is not covered in our market data.",
                    answer_value=None,
                    abstained=True,
                    refused=False,
                    reason="unsourced_instrument",
                    citations=[],
                    confidence=1.0,
                    agents=agent_roles
                )

        # 3. Routing Classification
        target_roles = []

        is_kyc = any(kw in prompt_lower for kw in ["kyc", "pan", "dob", "birth", "annual income", "income band", "bank account", "ifsc", "address", "risk profile", "employment", "employer", "identity", "occupation", "demat", "broker", "suitability"])
        is_notes = any(kw in prompt_lower for kw in ["note", "memo", "advisor", "review call", "interaction", "discussion", "comment", "remark", "observation"])
        is_market = any(kw in prompt_lower for kw in ["price", "sector", "industry", "news", "headline", "stock", "close", "listed", "exchange", "instrument", "currency", "market cap"])
        is_book = any(kw in prompt_lower for kw in ["cash", "balance", "position", "holding", "portfolio", "transaction", "deposit", "fee", "drift", "allocation", "quantity", "many", "how much", "share", "bought", "first bought", "dividend", "withdrawal", "funding", "settle", "disposal", "sell", "sold", "purchase", "trade", "total", "sum", "count", "open", "account age"])

        if is_notes:
            target_roles.append("notes_desk")

        if is_kyc:
            target_roles.append("kyc_profile")

        if is_market:
            target_roles.append("market_desk")

        if is_book or not target_roles:
            target_roles.append("book_qa")

        # 4. Dispatch to Specialists & Collect Answers
        answers = []
        citations = []
        primary_ans_val = None
        is_abstained = False
        is_conflict = False
        has_upstream_issue = False

        for role in target_roles:
            agent_roles.append(role)
            if role == "kyc_profile":
                ans_val, text_ans, cits = await kyc_profile_agent.process(prompt, cid)
            elif role == "notes_desk":
                ans_val, text_ans, cits = await notes_desk_agent.process(prompt, cid)
            elif role == "market_desk":
                ans_val, text_ans, cits = await market_desk_agent.process(prompt, cid)
            elif role == "book_qa":
                ans_val, text_ans, cits = await book_qa_agent.process(prompt, cid)
            else:
                continue

            # Detect upstream issue marker from agents
            if "[UPSTREAM_ISSUE]" in text_ans:
                has_upstream_issue = True
                text_ans = text_ans.replace(" [UPSTREAM_ISSUE]", "").replace("[UPSTREAM_ISSUE]", "")

            if ans_val is None and "conflict" in text_ans.lower():
                is_conflict = True
                is_abstained = True

            elif ans_val is None and not cits:
                is_abstained = True

            if ans_val and not primary_ans_val:
                primary_ans_val = str(ans_val)

            answers.append(text_ans)
            for c in cits:
                if isinstance(c, str) and c not in citations:
                    citations.append(c)

        response_flags = []
        if has_upstream_issue:
            response_flags.append("upstream_issue")

        if is_conflict:
            return AnswerResponse(
                question_id=qid,
                client_id=cid,
                answer="Disagreement detected between records.",
                answer_value=None,
                abstained=True,
                refused=False,
                reason="conflict",
                citations=citations,
                confidence=1.0,
                flags=["conflict"] + ([f for f in response_flags if f != "conflict"]),
                agents=agent_roles
            )

        final_answer_text = primary_ans_val if primary_ans_val else "\n\n".join(answers)

        if is_abstained and not primary_ans_val:
            return AnswerResponse(
                question_id=qid,
                client_id=cid,
                answer="Information not available in records.",
                answer_value=None,
                abstained=True,
                refused=False,
                reason="unanswerable",
                citations=[],
                confidence=1.0,
                flags=response_flags,
                agents=agent_roles
            )

        return AnswerResponse(
            question_id=qid,
            client_id=cid,
            answer=final_answer_text,
            answer_value=primary_ans_val,
            abstained=False,
            refused=False,
            reason=None,
            citations=citations if citations else ([cid] if cid else []),
            confidence=1.0,
            flags=response_flags,
            agents=agent_roles
        )

router_agent = RouterAgent()
