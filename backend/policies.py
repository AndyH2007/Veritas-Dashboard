def evaluate_policies(attestation: dict):
    claim = attestation.get("claims") or {}
    results = {}
    findings = []

    if claim.get("type") == "order":
        if claim.get("amount_usd", 0) <= 10000:
            results["trading.max_order_usd"] = "pass"
        else:
            results["trading.max_order_usd"] = "fail"
            findings.append(("fail", "POLICY:TRADING_MAX", "Order exceeds $10k"))

    status = "ok" if all(v == "pass" for v in results.values()) else "failed_policy"
    return status, results, findings
