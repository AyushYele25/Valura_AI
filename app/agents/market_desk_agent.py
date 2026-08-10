import json
import logging
import re
from typing import Tuple, List, Optional
from app.data.market_index import market_index
from app.llm.client import llm_client

logger = logging.getLogger(__name__)

class MarketDeskAgent:
    def extract_symbols(self, text: str) -> List[str]:
        candidates = re.findall(r'\b[A-Z]{2,10}\b', text)
        ignored = {"USD", "INR", "KYC", "PAN", "IFSC", "LRS", "T+1", "API", "CPU", "RAM", "POST", "GET", "WHAT", "HOW", "WHEN", "WHERE", "WHY", "IS", "ARE", "FOR", "THE", "AND"}
        return [c for c in candidates if c not in ignored]

    def _parse_dates(self, text: str) -> List[str]:
        dates = re.findall(r'\b20\d{2}-\d{2}-\d{2}\b', text)
        if dates:
            return sorted(dates)

        months = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12'
        }

        day_matches = re.findall(r'\b(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+(20\d{2})\b', text.lower())
        if day_matches:
            parsed = []
            for day, m_name, year in day_matches:
                day_str = day.zfill(2)
                m_num = months[m_name]
                parsed.append(f"{year}-{m_num}-{day_str}")
            return sorted(parsed)

        return []

    async def process(self, prompt: str, client_id: Optional[str] = None) -> Tuple[Optional[str], str, List[str]]:
        symbols = self.extract_symbols(prompt)
        prompt_lower = prompt.lower()

        # Check coverage
        uncovered = [s for s in symbols if not market_index.is_covered(s)]
        if uncovered:
            # Return None & empty citations so router marks as abstained (unsourced_instrument)
            return None, f"The symbol '{uncovered[0]}' is not covered in market data.", []

        parsed_dates = self._parse_dates(prompt)
        target_date = parsed_dates[0] if parsed_dates else "2026-07-31"

        # News summary query ("news", "articles", "coverage", "items", "published", "brief me")
        if any(kw in prompt_lower for kw in ["news", "article", "coverage", "items", "published", "brief"]):
            if symbols:
                sym = symbols[0]
                matching_news = [
                    n for n in market_index.news
                    if n.get("symbol") == sym and n.get("date", "") <= target_date
                ]
                count_str = str(len(matching_news))
                news_cits = [n.get("id") for n in matching_news if n.get("id")]

                summaries = [f"[{n.get('date')}] {n.get('headline')}: {n.get('body')}" for n in matching_news]
                text_ans = f"There are {count_str} news item(s) on file for {sym} up to {target_date}:\n" + "\n".join(summaries)

                return count_str, text_ans, news_cits

        # Market return query ("return", "performance", "percent")
        if any(kw in prompt_lower for kw in ["return", "performance", "percent"]):
            if len(parsed_dates) >= 2 and symbols:
                sym = symbols[0]
                res = market_index.get_market_return(sym, parsed_dates[0], parsed_dates[-1])
                if res:
                    ret_val, ret_sym = res
                    text = f"Percentage return for {ret_sym} between {parsed_dates[0]} and {parsed_dates[-1]}: {ret_val}%."
                    return ret_val, text, [ret_sym]

        if target_date > "2026-07-01":
            return None, f"No market price data available for date {target_date}.", []

        price_results = []
        inst_results = []
        ans_val = None
        citations = []

        for sym in symbols:
            if market_index.is_covered(sym):
                pinfo = market_index.get_price(sym, target_date)
                if pinfo:
                    price_results.append(pinfo)
                    if not ans_val:
                        ans_val = str(pinfo.get("close"))
                inst = market_index.get_instrument(sym)
                if inst:
                    inst_results.append(inst)
                citations.append(sym)

        news_items = market_index.get_news(symbols[0] if symbols else None, limit=3)

        context = {
            "requested_date": target_date,
            "prices": price_results,
            "instruments": inst_results,
            "news": news_items
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "You are market_desk agent. State the close price and the exact 'as_of_date' of the price."
                )
            },
            {
                "role": "user",
                "content": f"Market Context:\n{json.dumps(context)}\n\nPrompt: {prompt}"
            }
        ]

        text_ans = await llm_client.chat_completion(messages, model="valura-fast")
        if not text_ans:
            lines = [f"{p['symbol']} close on or before {p['target_date']} was USD {p['close']} (as of {p['as_of_date']})." for p in price_results]
            text_ans = "\n".join(lines) if lines else "Processed market query."

        return ans_val, text_ans, citations

market_desk_agent = MarketDeskAgent()
