import json
import logging
import re
from typing import Dict, Any, Tuple, Optional, List
from app.data.book_index import book_index
from app.utils.drift import calculate_portfolio_drift, get_single_symbol_drift
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

class BookQAAgent:
    def _parse_dates(self, text: str) -> List[str]:
        dates = re.findall(r'\b20\d{2}-\d{2}-\d{2}\b', text)
        if dates:
            return sorted(dates)

        months = {
            'january': ('01-01', '01-31'), 'february': ('02-01', '02-28'),
            'march': ('03-01', '03-31'), 'april': ('04-01', '04-30'),
            'may': ('05-01', '05-31'), 'june': ('06-01', '06-30'),
            'july': ('07-01', '07-31'), 'august': ('08-01', '08-31'),
            'september': ('09-01', '09-30'), 'october': ('10-01', '10-31'),
            'november': ('11-01', '11-30'), 'december': ('12-01', '12-31')
        }

        match = re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})\b', text.lower())
        if match:
            m_name, year = match.groups()
            s_day, e_day = months[m_name]
            return [f"{year}-{s_day}", f"{year}-{e_day}"]

        day_match = re.search(r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})\b', text.lower())
        if day_match:
            day, m_name, year = day_match.groups()
            day_str = day.zfill(2)
            m_num = months[m_name][0][:2]
            return [f"{year}-{m_num}-{day_str}"]

        year_match = re.search(r'\bin\s+(20\d{2})\b', text.lower())
        if year_match:
            y = year_match.group(1)
            return [f"{y}-01-01", f"{y}-12-31"]

        return []

    async def process(self, prompt: str, client_id: str) -> Tuple[Optional[str], str, List[str]]:
        client = book_index.get_client(client_id)
        if not client:
            return None, "Client not found in book.", []

        prompt_lower = prompt.lower()

        # Unanswerable transaction attributes
        unanswerable_attrs = ["execution venue", "venue", "clearing firm", "trader id", "settlement agent"]
        if any(attr in prompt_lower for attr in unanswerable_attrs):
            return None, "Transaction attribute is not recorded in client transaction logs.", []

        symbols = re.findall(r'\b[A-Z]{2,5}\b', prompt)
        ignored = {"USD", "INR", "KYC", "PAN", "IFSC", "LRS", "T+1", "API", "CPU", "RAM", "POST", "GET", "HOW", "MANY"}
        symbols = [s for s in symbols if s not in ignored]

        parsed_dates = self._parse_dates(prompt)
        as_of = parsed_dates[0] if parsed_dates else None

        # 1. Dividend sum query
        if "dividend" in prompt_lower or "dividends" in prompt_lower:
            sym = symbols[0] if symbols else "MSFT"
            s_date = parsed_dates[0] if len(parsed_dates) >= 1 else None
            e_date = parsed_dates[-1] if len(parsed_dates) >= 2 else s_date
            div_val, div_cits = book_index.get_sum_dividends(client_id, sym, start_date=s_date, end_date=e_date)
            text = f"Total dividends received by {client.get('name')} for {sym}: USD {div_val}."
            return div_val, text, div_cits

        # 2. Holdings quantity (as of date or current)
        if "distinct holdings" in prompt_lower or "how many holdings" in prompt_lower or "distinct positions" in prompt_lower:
            positions = book_index.get_positions(client_id)
            count_str = str(len(positions))
            text = f"{client.get('name')} has {count_str} distinct holdings."
            return count_str, text, [client_id]

        if "hold" in prompt_lower or "share" in prompt_lower or "shares" in prompt_lower or "quantity" in prompt_lower or "position size" in prompt_lower or "holding" in prompt_lower or "position" in prompt_lower:
            if symbols:
                sym = symbols[0]
                res = book_index.get_position_quantity_as_of(client_id, sym, as_of_date=as_of)
                if res:
                    qty_str, pos_cits = res
                    text = f"Client {client.get('name')} held {qty_str} shares of {sym} {'as at ' + as_of if as_of else 'currently'}."
                    return qty_str, text, pos_cits

        # 3. Biggest funding / deposit query
        if "biggest" in prompt_lower or "largest" in prompt_lower or "one-off funding" in prompt_lower:
            res = book_index.get_largest_funding(client_id)
            if res:
                amt_str, txn_cits = res
                text = f"Largest funding amount for {client.get('name')} was USD {amt_str}."
                return amt_str, text, txn_cits

        # 4. First purchase settlement date query
        if ("first" in prompt_lower or "purchase" in prompt_lower) and ("settle" in prompt_lower or "settled" in prompt_lower or "date" in prompt_lower or "bought" in prompt_lower):
            if symbols:
                sym = symbols[0]
                res = book_index.get_first_purchase_date(client_id, sym)
                if res:
                    settle_str, txn_cits = res
                    text = f"First purchase of {sym} for {client.get('name')} was on {settle_str}."
                    return settle_str, text, txn_cits

        # 5. Single symbol rebalance drift query
        if any(kw in prompt_lower for kw in ["holding away", "overweight", "underweight", "weight stand", "mandate", "percentage points", "drift"]):
            if symbols:
                sym = symbols[0]
                res = get_single_symbol_drift(client_id, sym)
                if res:
                    drift_val, drift_cits = res
                    text = f"Drift for {client.get('name')} in {sym} against target: {drift_val} percentage points."
                    return drift_val, text, drift_cits

        # 6. Account days open query
        if "days" in prompt_lower and ("open" in prompt_lower or "account" in prompt_lower or "age" in prompt_lower):
            res = book_index.get_account_days_open(client_id)
            if res:
                days_str, acc_id = res
                text = f"Account {acc_id} for {client.get('name')} has been open for {days_str} days as at the book date."
                return days_str, text, [acc_id]

        # 7. Sector exposure query
        sectors = ["communication services", "information technology", "consumer electronics", "semiconductors", "financials", "health care", "industrials"]
        matched_sector = next((s for s in sectors if s in prompt_lower), None)
        if matched_sector or ("sector" in prompt_lower or "proportion" in prompt_lower or "concentrated" in prompt_lower):
            sec_name = matched_sector or "Communication Services"
            res = book_index.get_sector_exposure(client_id, sec_name)
            if res:
                exp_pct_str, pos_cits = res
                text = f"{exp_pct_str}% of {client.get('name')}'s portfolio is in {sec_name}."
                return exp_pct_str, text, pos_cits

        # 8. Transaction count queries
        if "count" in prompt_lower or "how many" in prompt_lower or "disposals" in prompt_lower or "purchases" in prompt_lower:
            ttype = "sell" if ("sell" in prompt_lower or "disposal" in prompt_lower or "disposals" in prompt_lower) else ("buy" if ("purchase" in prompt_lower or "buy" in prompt_lower or "buys" in prompt_lower) else None)
            s_date = parsed_dates[0] if len(parsed_dates) >= 1 else None
            e_date = parsed_dates[1] if len(parsed_dates) >= 2 else s_date

            count = book_index.count_transactions(client_id, ttype=ttype, start_date=s_date, end_date=e_date)
            ans_val = str(count)
            text = f"Client {client.get('name')} made {count} {ttype or ''} transaction(s) in the specified period."
            return ans_val, text, [client_id]

        # 9. Total deposits / uninvested cash query
        if "deposit" in prompt_lower and ("total" in prompt_lower or "how much" in prompt_lower or "funded" in prompt_lower):
            s_date = parsed_dates[0] if len(parsed_dates) >= 1 else None
            e_date = parsed_dates[-1] if len(parsed_dates) >= 2 else s_date

            dep_sum = book_index.get_deposit_sum(client_id, start_date=s_date, end_date=e_date)
            ans_val = f"{dep_sum:.2f}"
            text = f"Total deposits by {client.get('name')} in period: USD {dep_sum:,.2f}."
            return ans_val, text, [client_id]

        if "cash" in prompt_lower or "balance" in prompt_lower or "uninvested" in prompt_lower:
            cash = book_index.get_cash_balance_as_of(client_id, as_of_date=as_of)
            ans_val = f"{cash:.2f}"
            text = f"Cash balance for {client.get('name')} {'as at ' + as_of if as_of else 'currently'}: USD {cash:,.2f}."
            return ans_val, text, [client_id]

        # 10. Portfolio Drift query
        if "drift" in prompt_lower or "allocation" in prompt_lower:
            drift_data = calculate_portfolio_drift(client_id)
            if drift_data:
                lines = [f"Portfolio drift for {client.get('name')}:"]
                for sym, d in drift_data['symbol_drift'].items():
                    lines.append(f"- {sym}: Actual {d['actual_pct']}%, Target {d['target_pct']}%, Drift {d['drift_pct']:+}%")
                return None, "\n".join(lines), [client_id]

        # Fallback LLM query
        positions = book_index.get_positions(client_id)
        context = {
            "client_id": client_id,
            "name": client.get("name"),
            "cash_usd": book_index.get_cash_balance_as_of(client_id),
            "positions": positions
        }

        messages = [
            {"role": "system", "content": "You are book_qa. Answer precisely from context."},
            {"role": "user", "content": f"Context:\n{json.dumps(context)}\n\nPrompt: {prompt}"}
        ]

        text_ans = await llm_client.chat_completion(messages, model="valura-fast")
        return None, text_ans or "Processed book QA query.", [client_id]

book_qa_agent = BookQAAgent()
