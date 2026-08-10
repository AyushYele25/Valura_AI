import re
from typing import Dict, Any, Tuple
from app.data.book_index import book_index

class ComplianceAgent:
    def check_refusal(self, prompt: str, client_id: str, is_client_valid: bool, mentioned_symbols: list, covered_symbols: set) -> Tuple[bool, str, str]:
        """
        Returns (is_refusal, refusal_reason, refusal_category)
        """
        prompt_lower = prompt.lower()

        # 1. Out of scope client check
        if client_id and not is_client_valid:
            return True, f"Client ID '{client_id}' is outside the authorized client book.", "out_of_scope"

        # 2. Cross-client access check
        other_cids = re.findall(r'\bcli_\d{4}\b', prompt)
        if client_id and other_cids:
            if any(c != client_id for c in other_cids):
                return True, "Cross-client querying across multiple accounts is not permitted.", "cross_client"

        client_count = 0
        current_client = book_index.get_client(client_id) if client_id else None
        curr_name = current_client.get("name", "").lower() if current_client else ""

        for name, c_record in book_index.clients_by_name.items():
            if name in prompt_lower:
                if curr_name and name not in curr_name and curr_name not in name:
                    return True, "Cross-client querying across multiple accounts is not permitted.", "cross_client"
                client_count += 1
        if client_count > 1:
            return True, "Cross-client querying across multiple accounts is not permitted.", "cross_client"

        # 3. Personalised advice check
        advice_patterns = [
            r'should\s+.*\s+(buy|sell|invest|rebalance|allocate|hold|move|put)',
            r'should\s+they', r'is\s+(now\s+)?a\s+good\s+time',
            r'good\s+time\s+to\s+(buy|sell|exit|move)',
            r'safer\s+assets', r'move\s+into', r'put\s+more\s+money',
            r'tell\s+.*\s+to\s+(put|invest|buy|sell)',
            r'recommend', r'recommendation', r'what\s+should\s+the\s+target\s+be',
            r'suggest\s+allocation', r'financial\s+advice', r'worth\s+(buying|selling)'
        ]
        for pattern in advice_patterns:
            if re.search(pattern, prompt_lower):
                return True, "Personalized investment advice and target allocation recommendations are out of scope.", "advice"

        return False, "", ""

compliance_agent = ComplianceAgent()
