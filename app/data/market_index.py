import logging
from typing import Optional, Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)

class MarketIndex:
    def __init__(self):
        self.meta: Dict[str, Any] = {}
        self.covered_symbols: Set[str] = set()
        self.instruments: Dict[str, Dict[str, Any]] = {}
        self.prices: Dict[str, List[Dict[str, str]]] = {}
        self.news: List[Dict[str, Any]] = []

    def load(self, data: Dict[str, Any]):
        self.meta = data.get("meta", {})
        self.covered_symbols = set(self.meta.get("covered_symbols", []))
        self.instruments.clear()
        self.prices.clear()
        self.news = data.get("news", [])

        for inst in data.get("instruments", []):
            sym = inst.get("symbol")
            if sym:
                self.instruments[sym] = inst

        for sym, plist in data.get("prices", {}).items():
            sorted_p = sorted(plist, key=lambda x: x.get("date", ""))
            self.prices[sym] = sorted_p

        logger.info(f"Loaded MarketIndex with covered symbols: {self.covered_symbols}")

    def is_covered(self, symbol: str) -> bool:
        return symbol.upper() in self.covered_symbols

    def get_instrument(self, symbol: str) -> Optional[Dict[str, Any]]:
        return self.instruments.get(symbol.upper())

    def get_price(self, symbol: str, target_date: str) -> Optional[Dict[str, Any]]:
        sym = symbol.upper()
        if not self.is_covered(sym):
            return None

        plist = self.prices.get(sym, [])
        applicable = [p for p in plist if p.get("date", "") <= target_date]
        if not applicable:
            return plist[0] if plist else None

        most_recent = applicable[-1]
        return {
            "symbol": sym,
            "target_date": target_date,
            "as_of_date": most_recent.get("date"),
            "close": most_recent.get("close")
        }

    def get_market_return(self, symbol: str, start_date: str, end_date: str) -> Optional[Tuple[str, str]]:
        """
        Calculates percentage return: ((price_end - price_start) / price_start) * 100.0
        Returns (return_pct_str, symbol)
        """
        sym = symbol.upper()
        if not self.is_covered(sym):
            return None

        p_start = self.get_price(sym, start_date)
        p_end = self.get_price(sym, end_date)

        if not p_start or not p_end:
            return None

        c_start = float(p_start["close"])
        c_end = float(p_end["close"])

        if c_start == 0:
            return None

        ret_pct = ((c_end - c_start) / c_start) * 100.0
        return f"{ret_pct:.2f}", sym

    def get_news(self, symbol: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        if symbol:
            sym = symbol.upper()
            filtered = [n for n in self.news if n.get("symbol") == sym]
            return filtered[:limit]
        return self.news[:limit]

market_index = MarketIndex()
