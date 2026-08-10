import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from app.data.market_index import market_index

logger = logging.getLogger(__name__)

class BookIndex:
    def __init__(self):
        self.meta: Dict[str, Any] = {}
        self.clients_by_id: Dict[str, Dict[str, Any]] = {}
        self.clients_by_name: Dict[str, Dict[str, Any]] = {}

    def load(self, data: Dict[str, Any]):
        self.meta = data.get("meta", {})
        self.clients_by_id.clear()
        self.clients_by_name.clear()

        for client in data.get("clients", []):
            cid = client.get("id")
            name = client.get("name", "")
            if cid:
                self.clients_by_id[cid] = client
            if name:
                self.clients_by_name[name.lower()] = client

        logger.info(f"Loaded {len(self.clients_by_id)} clients into BookIndex.")

    def get_client(self, client_id: str) -> Optional[Dict[str, Any]]:
        return self.clients_by_id.get(client_id)

    def find_client_by_name(self, name_query: str) -> Optional[Dict[str, Any]]:
        query = name_query.lower().strip()
        if query in self.clients_by_name:
            return self.clients_by_name[query]
        for name, client in self.clients_by_name.items():
            if query in name or name in query:
                return client
        return None

    def get_positions(self, client_id: str) -> List[Dict[str, Any]]:
        client = self.get_client(client_id)
        if not client:
            return []
        return client.get("positions_snapshot", [])

    def get_transactions(self, client_id: str) -> List[Dict[str, Any]]:
        client = self.get_client(client_id)
        if not client:
            return []
        return client.get("transactions", [])

    def get_fee_sum(self, client_id: str) -> Tuple[str, List[str]]:
        txns = self.get_transactions(client_id)
        fee_txns = []
        total_fees = 0.0
        for t in txns:
            ttype = t.get("type", "").lower()
            f_usd = float(t.get("fees_usd") or 0.0)
            a_usd = float(t.get("amount_usd") or 0.0)
            if ttype == "fee":
                total_fees += a_usd
                fee_txns.append(t.get("id"))
            elif f_usd > 0:
                total_fees += f_usd
                fee_txns.append(t.get("id"))
        return f"{total_fees:.2f}", [client_id]

    def check_risk_profile_conflict(self, client_id: str) -> Optional[Tuple[None, str, List[str]]]:
        client = self.get_client(client_id)
        if not client:
            return None
        kyc = client.get("kyc", {})
        reviews = client.get("suitability_reviews", [])
        kyc_risk = kyc.get("risk_profile", "").lower()
        kyc_id = kyc.get("id", f"kyc_{client_id.replace('cli_', '')}")

        if reviews:
            latest_rev = reviews[-1]
            rev_risk = latest_rev.get("risk_profile", "").lower()
            rev_id = latest_rev.get("id")
            if kyc_risk and rev_risk and kyc_risk != rev_risk:
                return None, f"Conflict between KYC risk profile ({kyc_risk}) and suitability review ({rev_risk}).", [kyc_id, rev_id]
        return None

    def check_kyc_standing_conflict(self, client_id: str) -> Optional[Tuple[None, str, List[str]]]:
        client = self.get_client(client_id)
        if not client:
            return None
        kyc = client.get("kyc", {})
        notes = client.get("notes", [])
        kyc_id = kyc.get("id", f"kyc_{client_id.replace('cli_', '')}")

        flagged_notes = []
        for n in notes:
            n_text = n.get("text", "").lower()
            if any(w in n_text for w in ["expired", "pending", "discrepancy", "flagged", "missing", "incomplete", "kyc"]):
                flagged_notes.append(n.get("id"))

        if kyc.get("kyc_status", "").lower() == "verified" and flagged_notes:
            return None, "Disagreement between verified KYC record and notes indicating pending/flagged issues.", [kyc_id, flagged_notes[0]]
        return None

    def check_position_conflict(self, client_id: str, symbol: str) -> Optional[Tuple[None, str, List[str]]]:
        pos = self.get_holding_quantity(client_id, symbol)
        if not pos:
            return None
        pos_id = pos.get("id", f"pos_{client_id}_{symbol.upper()}")
        txns = self.get_transactions(client_id)
        sym_upper = symbol.upper()
        sym_txns = [t for t in txns if t.get("symbol", "").upper() == sym_upper]

        # Calculate position from buys/sells
        calc_qty = 0.0
        matching_ids = [pos_id]
        for t in sym_txns:
            ttype = t.get("type", "").lower()
            tqty = float(t.get("quantity", 0.0))
            if ttype in ("buy", "purchase"):
                calc_qty += tqty
                matching_ids.append(t.get("id"))
            elif ttype in ("sell", "disposal"):
                calc_qty -= tqty
                matching_ids.append(t.get("id"))

        snap_qty = float(pos.get("quantity", 0.0))
        if abs(calc_qty - snap_qty) > 0.001 and len(sym_txns) > 1:
            return None, f"Disagreement between position snapshot ({snap_qty}) and transaction history ({calc_qty:.4f}).", matching_ids[:5]
        return None

    def count_transactions(self, client_id: str, ttype: Optional[str] = None, symbol: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> int:
        txns = self.get_transactions(client_id)
        count = 0
        sym_upper = symbol.upper() if symbol else None

        for t in txns:
            tdate = t.get("date", "")
            tp = t.get("type", "").lower()

            if start_date and tdate < start_date:
                continue
            if end_date and tdate > end_date:
                continue
            if sym_upper and t.get("symbol", "").upper() != sym_upper:
                continue

            if ttype:
                if ttype in ("sell", "disposal") and tp not in ("sell", "disposal"):
                    continue
                if ttype in ("buy", "purchase") and tp not in ("buy", "purchase"):
                    continue
                if ttype == "deposit" and tp != "deposit":
                    continue

            count += 1
        return count

    def get_deposit_sum(self, client_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, use_inr: bool = False) -> float:
        txns = self.get_transactions(client_id)
        total = 0.0
        for t in txns:
            tdate = t.get("date", "")
            tp = t.get("type", "").lower()

            if start_date and tdate < start_date:
                continue
            if end_date and tdate > end_date:
                continue

            if tp == "deposit":
                if use_inr and "amount_inr" in t:
                    amt = float(t.get("amount_inr", 0.0))
                else:
                    amt = float(t.get("amount_usd") or t.get("net_usd", 0.0))
                total += amt
        return round(total, 2)

    def get_cash_balance_as_of(self, client_id: str, as_of_date: Optional[str] = None) -> float:
        client = self.get_client(client_id)
        if not client:
            return 0.0

        cash = 0.0
        for txn in client.get("transactions", []):
            tdate = txn.get("date", "")
            if as_of_date and tdate > as_of_date:
                continue

            ttype = txn.get("type", "").lower()
            amt = float(txn.get("net_usd") or txn.get("amount_usd", 0.0))
            if ttype in ("deposit", "interest", "dividend", "sell"):
                cash += amt
            elif ttype in ("withdrawal", "fee", "buy"):
                cash -= amt
        return round(cash, 2)

    def get_position_quantity_as_of(self, client_id: str, symbol: str, as_of_date: Optional[str] = None) -> Optional[Tuple[str, List[str]]]:
        pos = self.get_holding_quantity(client_id, symbol)
        if not pos:
            return None

        qty = float(pos.get("quantity", 0.0))
        pos_id = pos.get("id", f"pos_{client_id}_{symbol.upper()}")

        if as_of_date and as_of_date < self.meta.get("as_of", "2026-07-31"):
            txns = self.get_transactions(client_id)
            sym_upper = symbol.upper()
            for t in txns:
                tdate = t.get("date", "")
                if tdate > as_of_date and t.get("symbol", "").upper() == sym_upper:
                    ttype = t.get("type", "").lower()
                    tqty = float(t.get("quantity", 0.0))
                    if ttype in ("buy", "purchase"):
                        qty -= tqty
                    elif ttype in ("sell", "disposal"):
                        qty += tqty

        formatted_qty = f"{qty:.4f}".rstrip('0').rstrip('.') if qty % 1 != 0 else str(int(qty))
        return formatted_qty, [pos_id]

    def get_largest_funding(self, client_id: str) -> Optional[Tuple[str, List[str]]]:
        txns = self.get_transactions(client_id)
        deposits = [t for t in txns if t.get("type", "").lower() == "deposit"]
        if not deposits:
            return None
        max_dep = max(deposits, key=lambda x: float(x.get("amount_usd") or x.get("net_usd", 0.0)))
        amt = float(max_dep.get("amount_usd") or max_dep.get("net_usd", 0.0))
        return f"{amt:.2f}", [max_dep.get("id")]

    def get_sum_dividends(self, client_id: str, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[str, List[str]]:
        txns = self.get_transactions(client_id)
        sym_upper = symbol.upper()
        divs = []
        for t in txns:
            if t.get("type", "").lower() == "dividend" and t.get("symbol", "").upper() == sym_upper:
                tdate = t.get("date", "")
                if start_date and tdate < start_date:
                    continue
                if end_date and tdate > end_date:
                    continue
                divs.append(t)

        total = sum(float(t.get("net_usd") or t.get("amount_usd", 0.0)) for t in divs)
        cits = [t.get("id") for t in divs if t.get("id")]
        return f"{total:.2f}", cits

    def get_first_purchase_date(self, client_id: str, symbol: str) -> Optional[Tuple[str, List[str]]]:
        txns = self.get_transactions(client_id)
        sym_upper = symbol.upper()
        buys = [t for t in txns if t.get("type", "").lower() in ("buy", "purchase") and t.get("symbol", "").upper() == sym_upper]
        if not buys:
            return None
        sorted_buys = sorted(buys, key=lambda x: x.get("date", ""))
        first_buy = sorted_buys[0]
        trade_date = first_buy.get("date", "")
        return trade_date, [first_buy.get("id")]

    def get_account_days_open(self, client_id: str) -> Optional[Tuple[str, str]]:
        client = self.get_client(client_id)
        if not client:
            return None
        accounts = client.get("accounts", [])
        if not accounts:
            return None
        acc = accounts[0]
        opened = acc.get("opened")
        acc_id = acc.get("id", f"acc_{client_id.replace('cli_', '')}")
        as_of = self.meta.get("as_of", "2026-07-31")
        if opened:
            d_open = datetime.strptime(opened, "%Y-%m-%d")
            d_ref = datetime.strptime(as_of, "%Y-%m-%d")
            days = (d_ref - d_open).days
            return str(days), acc_id
        return None

    def get_sector_exposure(self, client_id: str, sector_name: str) -> Optional[Tuple[str, List[str]]]:
        positions = self.get_positions(client_id)
        if not positions:
            return None

        total_value = sum(float(p.get("market_value_usd", 0.0)) for p in positions)
        if total_value == 0:
            return None

        sector_value = 0.0
        matching_citations = []

        for p in positions:
            sym = p.get("symbol")
            inst = market_index.get_instrument(sym)
            if inst and inst.get("sector", "").lower() == sector_name.lower():
                val = float(p.get("market_value_usd", 0.0))
                sector_value += val
                pos_id = p.get("id", f"pos_{client_id}_{sym}")
                matching_citations.append(pos_id)

        if not matching_citations:
            return None

        pct = round((sector_value / total_value) * 100.0, 2)
        return f"{pct:.2f}", matching_citations

    def get_holding_quantity(self, client_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        positions = self.get_positions(client_id)
        sym_upper = symbol.upper()
        for p in positions:
            if p.get("symbol", "").upper() == sym_upper:
                return p
        return None

    def get_kyc(self, client_id: str) -> Optional[Dict[str, Any]]:
        client = self.get_client(client_id)
        if not client:
            return None
        return client.get("kyc")

    def get_target_allocation(self, client_id: str) -> Optional[Dict[str, float]]:
        client = self.get_client(client_id)
        if not client:
            return None
        reviews = client.get("suitability_reviews", [])
        if not reviews:
            return None
        latest = reviews[-1]
        target = latest.get("target_allocation_pct", {})
        return {k: float(v) for k, v in target.items()}

    def get_notes(self, client_id: str) -> List[Dict[str, Any]]:
        client = self.get_client(client_id)
        if not client:
            return []
        return client.get("notes", [])

book_index = BookIndex()
