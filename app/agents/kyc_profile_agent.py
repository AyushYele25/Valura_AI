import json
import logging
from typing import Tuple, Optional, List
from app.data.book_index import book_index
from app.utils.masking import mask_kyc_record
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

class KYCProfileAgent:
    async def process(self, prompt: str, client_id: str) -> Tuple[Optional[str], str, List[str]]:
        client = book_index.get_client(client_id)
        if not client:
            return None, "Client not found.", []

        prompt_lower = prompt.lower()

        # Check conflict for risk profile
        if "risk profile" in prompt_lower or "risk" in prompt_lower:
            conflict = book_index.check_risk_profile_conflict(client_id)
            if conflict:
                val, text, cits = conflict
                return val, text, cits

        # Check conflict for KYC standing / complete
        if "complete" in prompt_lower or "good standing" in prompt_lower or "standing" in prompt_lower:
            conflict = book_index.check_kyc_standing_conflict(client_id)
            if conflict:
                val, text, cits = conflict
                return val, text, cits

        raw_kyc = book_index.get_kyc(client_id) or {}
        masked_kyc = mask_kyc_record(raw_kyc)
        kyc_id = raw_kyc.get("id", f"kyc_{client_id.replace('cli_', '')}")
        citations = [kyc_id]

        reviews = client.get("suitability_reviews", [])
        if reviews:
            rev_id = reviews[-1].get("id")
            if rev_id and rev_id not in citations:
                citations.append(rev_id)

        ans_val = None

        # Employer query
        if "employer" in prompt_lower or "work" in prompt_lower or "employed" in prompt_lower or "company" in prompt_lower:
            employment = raw_kyc.get("employment", {})
            emp = employment.get("employer") or employment.get("company") or raw_kyc.get("employer") or raw_kyc.get("company")
            if emp:
                ans_val = str(emp)
            else:
                return None, f"Employer information for {client.get('name')} is not available in the KYC record.", []

        # Risk profile query
        elif "risk profile" in prompt_lower or "risk" in prompt_lower:
            rprof = raw_kyc.get("risk_profile")
            if rprof:
                ans_val = str(rprof)

        # PAN / Identity number query
        elif "pan" in prompt_lower or "identity" in prompt_lower:
            pan = masked_kyc.get("pan")
            if pan:
                ans_val = str(pan)

        # Bank account query
        elif any(kw in prompt_lower for kw in ["bank account", "account number", "account", "bank", "digits"]):
            bank_acc = masked_kyc.get("bank_account", {})
            if isinstance(bank_acc, dict):
                ans_val = bank_acc.get("account_number")

        # DOB query
        elif "dob" in prompt_lower or "birth" in prompt_lower:
            dob = raw_kyc.get("date_of_birth")
            if dob:
                ans_val = str(dob)

        context = {
            "client_id": client_id,
            "name": client.get("name"),
            "kyc": masked_kyc
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are kyc_profile agent. Answer the prompt accurately based on KYC data. "
                    "Keep PAN and bank accounts masked as provided."
                )
            },
            {
                "role": "user",
                "content": f"KYC Context:\n{json.dumps(context)}\n\nPrompt: {prompt}"
            }
        ]

        text_ans = await llm_client.chat_completion(messages, model="valura-fast")
        if text_ans == "__UPSTREAM_ISSUE__":
            text_ans = f"KYC information for {client.get('name')}: Status is '{masked_kyc.get('kyc_status')}'. [UPSTREAM_ISSUE]"
        elif not text_ans:
            text_ans = f"KYC information for {client.get('name')}: Status is '{masked_kyc.get('kyc_status')}'."

        return ans_val, text_ans, citations

kyc_profile_agent = KYCProfileAgent()
