# backend/policies.py
from typing import Dict, Any, List, Tuple

"""
Returns:
  status: "ok" or "failed_policy"
  findings: list of {code, message, severity}
"""
def evaluate_policies(bundle: Dict[str, Any], meta: Dict[str, Any] | None) -> tuple[str, List[Dict[str, str]]]:
    findings: List[Dict[str, str]] = []

    # Guard: if no metadata, nothing to check
    if not meta:
        return "ok", findings

    # --- Example Rule 1: Trading max order size ---
    # If the action is an order, require amount_usd <= 10000
    if meta.get("type") == "order":
        amt = meta.get("amount_usd")
        if isinstance(amt, (int, float)) and amt > 10_000:
            findings.append({
                "code": "TRADING_MAX",
                "message": f"Order amount ${amt:,.0f} exceeds $10,000 limit",
                "severity": "high",
            })

    # You can add more rules here later (data-access, PII, model version allowlist, etc.)

    status = "ok" if not findings else "failed_policy"
    return status, findings
