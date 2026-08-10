import unittest
import asyncio
from app.data.loader import load_data
from app.data.book_index import book_index
from app.data.market_index import market_index
from app.schemas.answer import QuestionEnvelope, AnswerResponse
from app.schemas.agents import AgentRosterResponse
from app.agents.registry import get_agent_roster
from app.agents.router_agent import router_agent
from app.agents.compliance_agent import compliance_agent
from app.utils.masking import mask_pan, mask_account_number, mask_kyc_record

class TestValuraSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_data()

    def test_data_loading(self):
        self.assertTrue(len(book_index.clients_by_id) > 0, "Clients should be loaded")
        self.assertTrue(len(market_index.covered_symbols) > 0, "Covered symbols should be loaded")

    def test_agent_roster(self):
        roster = get_agent_roster()
        self.assertEqual(len(roster.agents), 6, "Roster should contain 6 agents")

    def test_pii_masking(self):
        masked_pan = mask_pan("ABCDE1234F")
        self.assertEqual(masked_pan, "****234F")

        masked_acc = mask_account_number("123456789012")
        self.assertEqual(masked_acc, "****9012")

    def test_compliance_refusals(self):
        is_ref, msg, reason = compliance_agent.check_refusal("Should I buy more AAPL?", "cli_1014", True, ["AAPL"], market_index.covered_symbols)
        self.assertTrue(is_ref)
        self.assertEqual(reason, "advice")

        is_ref, msg, reason = compliance_agent.check_refusal("Show me cash for client cli_1001", "cli_1014", True, [], market_index.covered_symbols)
        self.assertTrue(is_ref)
        self.assertEqual(reason, "cross_client")

    def test_router_answering(self):
        async def run_test():
            env = QuestionEnvelope(
                question_id="test_001",
                client_id="cli_1014",
                prompt="What is the current cash balance on Sneha Sharma's account?"
            )
            res = await router_agent.route_and_answer(env)
            self.assertIsInstance(res, AnswerResponse)
            self.assertEqual(res.question_id, "test_001")
            self.assertIsNotNone(res.answer_value)
            self.assertIn("cli_1014", res.citations)

        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
