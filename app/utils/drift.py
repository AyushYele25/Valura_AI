from typing import Dict, Any, Optional, Tuple, List
from app.data.book_index import book_index

def calculate_portfolio_drift(client_id: str) -> Optional[Dict[str, Any]]:
    client = book_index.get_client(client_id)
    if not client:
        return None

    positions = book_index.get_positions(client_id)
    target_alloc = book_index.get_target_allocation(client_id)

    if not positions or not target_alloc:
        return None

    total_value = sum(float(p.get("market_value_usd", 0.0)) for p in positions)
    if total_value == 0:
        return None

    actual_alloc = {}
    for p in positions:
        sym = p.get("symbol")
        val = float(p.get("market_value_usd", 0.0))
        actual_alloc[sym] = round((val / total_value) * 100.0, 2)

    drift_report = {}
    all_symbols = set(actual_alloc.keys()) | set(target_alloc.keys())

    for sym in sorted(all_symbols):
        actual = actual_alloc.get(sym, 0.0)
        target = target_alloc.get(sym, 0.0)
        drift = round(actual - target, 2)
        drift_report[sym] = {
            "actual_pct": actual,
            "target_pct": target,
            "drift_pct": drift,
            "status": "overweight" if drift > 0 else ("underweight" if drift < 0 else "on_target")
        }

    return {
        "client_id": client_id,
        "total_portfolio_value_usd": round(total_value, 2),
        "symbol_drift": drift_report
    }

def get_single_symbol_drift(client_id: str, symbol: str) -> Optional[Tuple[str, List[str]]]:
    """
    Calculates single symbol drift: actual_weight_pct - target_weight_pct
    Returns (drift_pct_str, [pos_id, rev_id])
    """
    client = book_index.get_client(client_id)
    if not client:
        return None

    positions = book_index.get_positions(client_id)
    target_alloc = book_index.get_target_allocation(client_id)

    if not positions or not target_alloc:
        return None

    total_value = sum(float(p.get("market_value_usd", 0.0)) for p in positions)
    if total_value == 0:
        return None

    sym_upper = symbol.upper()
    target_pct = target_alloc.get(sym_upper)
    if target_pct is None:
        return None

    target_pct = float(target_pct)

    pos = next((p for p in positions if p.get("symbol", "").upper() == sym_upper), None)
    actual_pct = 0.0
    pos_id = f"pos_{client_id}_{sym_upper}"

    if pos:
        actual_val = float(pos.get("market_value_usd", 0.0))
        actual_pct = (actual_val / total_value) * 100.0
        pos_id = pos.get("id", pos_id)

    drift_pct = round(actual_pct - target_pct, 2)
    drift_str = f"{drift_pct:.2f}"

    citations = [pos_id]
    reviews = client.get("suitability_reviews", [])
    if reviews:
        rev_id = reviews[-1].get("id")
        if rev_id and rev_id not in citations:
            citations.append(rev_id)

    return drift_str, citations
