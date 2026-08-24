import json
import logging
import re
from typing import Tuple, Optional, List
from app.data.book_index import book_index
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

class NotesDeskAgent:
    async def process(self, prompt: str, client_id: str) -> Tuple[Optional[str], str, List[str]]:
        client = book_index.get_client(client_id)
        if not client:
            return None, "Client not found.", []

        prompt_lower = prompt.lower()
        notes = book_index.get_notes(client_id)
        citations = []

        # Check if query asks about a specific transaction memo (e.g. txn_107648)
        txn_matches = re.findall(r'\btxn_\d+\b', prompt)
        if txn_matches:
            citations.extend(txn_matches)
            txns = book_index.get_transactions(client_id)
            matched_txns = [t for t in txns if t.get("id") in txn_matches]
            memo_texts = [f"Transaction {t['id']}: {t.get('description', '')}" for t in matched_txns if t.get('description')]
            text_ans = "\n".join(memo_texts) if memo_texts else f"Memo details for transaction {txn_matches[0]}."
            return None, text_ans, citations

        # Default notes queries: cite all matching note IDs
        if notes:
            citations = [n.get("id") for n in notes if n.get("id")]

        if not notes:
            return None, f"No advisor notes found for client {client.get('name')} ({client_id}).", [client_id]

        context = {
            "client_id": client_id,
            "name": client.get("name"),
            "notes": notes
        }

        messages = [
            {
                "role": "system",
                "content": "You are notes_desk agent. Summarise client notes accurately."
            },
            {
                "role": "user",
                "content": f"Notes Context:\n{json.dumps(context)}\n\nPrompt: {prompt}"
            }
        ]

        text_ans = await llm_client.chat_completion(messages, model="valura-fast")
        if text_ans == "__UPSTREAM_ISSUE__":
            note_summary = " | ".join([f"[{n.get('date')}] {n.get('text')}" for n in notes])
            text_ans = f"Notes for {client.get('name')}: {note_summary} [UPSTREAM_ISSUE]"
        elif not text_ans:
            note_summary = " | ".join([f"[{n.get('date')}] {n.get('text')}" for n in notes])
            text_ans = f"Notes for {client.get('name')}: {note_summary}"

        return None, text_ans, citations

notes_desk_agent = NotesDeskAgent()
