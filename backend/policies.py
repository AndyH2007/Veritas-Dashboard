# backend/policies.py
"""
Policy Evaluation System with Risk Analysis Integration
Combines rule-based policies with ML-powered risk detection
"""

from typing import Dict, Any, List, Tuple

def evaluate_policies(
    attestation: Dict[str, Any]
) -> Tuple[str, Dict[str, Any], List[Tuple[str, str, str]]]:
    """
    Evaluate policies on an attestation.
    
    Args:
        attestation: Full attestation data with model info, inputs, outputs
    
    Returns:
        (status, summary, findings)
        - status: "pass" or "fail"
        - summary: dict with stats
        - findings: list of (severity, code, message) tuples
    """
    findings: List[Tuple[str, str, str]] = []
    
    # Extract relevant fields
    model_name = attestation.get("model_name", "")
    inputs = attestation.get("params", {}).get("inputs", {})
    outputs = attestation.get("params", {}).get("outputs", {})
    claims = attestation.get("claims", {})
    
    # --- Rule 1: Model Allowlist ---
    approved_models = [
        "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini",
        "claude-3-opus", "claude-3-sonnet", "claude-3-haiku",
        "gemini-pro", "llama-3-70b"
    ]
    
    if model_name and not any(m in model_name.lower() for m in approved_models):
        findings.append((
            "medium",
            "UNAPPROVED_MODEL",
            f"Model '{model_name}' is not on the approved list"
        ))
    
    # --- Rule 2: Confidence Threshold ---
    confidence = claims.get("confidence") or claims.get("accuracy")
    if confidence is not None:
        if confidence < 0.7:
            findings.append((
                "high",
                "LOW_CONFIDENCE",
                f"Model confidence ({confidence:.2%}) below 70% threshold"
            ))
        elif confidence < 0.8:
            findings.append((
                "medium",
                "MODERATE_CONFIDENCE",
                f"Model confidence ({confidence:.2%}) below recommended 80%"
            ))
    
    # --- Rule 3: Input Validation ---
    if not inputs:
        findings.append((
            "low",
            "MISSING_INPUTS",
            "No inputs provided in attestation"
        ))
    
    if not outputs:
        findings.append((
            "low",
            "MISSING_OUTPUTS",
            "No outputs provided in attestation"
        ))
    
    # --- Rule 4: PII Detection ---
    text_content = str(inputs) + str(outputs)
    pii_keywords = ["ssn", "social security", "credit card", "password", "secret"]
    
    for keyword in pii_keywords:
        if keyword in text_content.lower():
            findings.append((
                "high",
                "PII_DETECTED",
                f"Potential PII detected: '{keyword}'"
            ))
    
    # --- Rule 5: Output Size Limits ---
    output_str = str(outputs)
    if len(output_str) > 50_000:  # 50KB limit
        findings.append((
            "medium",
            "LARGE_OUTPUT",
            f"Output size ({len(output_str)} chars) exceeds 50KB limit"
        ))
    
    # --- Rule 6: Execution Time Limits ---
    started_at = attestation.get("started_at", 0)
    finished_at = attestation.get("finished_at", 0)
    duration = finished_at - started_at
    
    if duration > 300:  # 5 minutes
        findings.append((
            "medium",
            "LONG_EXECUTION",
            f"Execution took {duration:.1f}s (exceeds 5min limit)"
        ))
    
    # Calculate summary stats
    summary = {
        "total_checks": 6,
        "passed": 6 - len(findings),
        "failed": len(findings),
        "high_severity": sum(1 for f in findings if f[0] == "high"),
        "medium_severity": sum(1 for f in findings if f[0] == "medium"),
        "low_severity": sum(1 for f in findings if f[0] == "low")
    }
    
    # Determine overall status
    has_high_severity = any(f[0] == "high" for f in findings)
    status = "fail" if has_high_severity else "pass"
    
    return status, summary, findings


def evaluate_action_policies(
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    meta: Dict[str, Any] | None = None
) -> Tuple[str, List[Dict[str, str]]]:
    """
    Simplified policy evaluation for action logging (pre-blockchain).
    Used by the risk oracle for quick checks.
    
    Returns:
        (status, findings)
        - status: "ok" or "failed_policy"
        - findings: list of {code, message, severity} dicts
    """
    findings: List[Dict[str, str]] = []
    
    # Guard: if no metadata, nothing to check
    if not meta:
        return "ok", findings
    
    # --- Rule 1: Trading max order size ---
    if meta.get("type") == "order":
        amt = meta.get("amount_usd")
        if isinstance(amt, (int, float)) and amt > 10_000:
            findings.append({
                "code": "TRADING_MAX",
                "message": f"Order amount ${amt:,.0f} exceeds $10,000 limit",
                "severity": "high",
            })
    
    # --- Rule 2: Medical advice confidence ---
    if meta.get("type") == "medical":
        confidence = outputs.get("confidence", 1.0)
        if confidence < 0.9:
            findings.append({
                "code": "LOW_MEDICAL_CONFIDENCE",
                "message": f"Medical advice confidence {confidence:.2%} below 90% threshold",
                "severity": "high",
            })
    
    # --- Rule 3: Legal disclaimer check ---
    if meta.get("type") == "legal":
        output_text = str(outputs).lower()
        if "disclaimer" not in output_text and "not legal advice" not in output_text:
            findings.append({
                "code": "MISSING_LEGAL_DISCLAIMER",
                "message": "Legal output missing required disclaimer",
                "severity": "medium",
            })
    
    # --- Rule 4: Data access limits ---
    if "database" in str(inputs).lower() or "query" in str(inputs).lower():
        # Check for SELECT statements (reads) vs modifications
        query_text = str(inputs).lower()
        dangerous_sql = ["drop", "delete", "truncate", "alter", "update"]
        
        for keyword in dangerous_sql:
            if keyword in query_text:
                findings.append({
                    "code": "DANGEROUS_SQL",
                    "message": f"Potentially dangerous SQL operation: {keyword.upper()}",
                    "severity": "high",
                })
    
    # --- Rule 5: Rate limiting check (via meta) ---
    if meta.get("requests_last_minute", 0) > 60:
        findings.append({
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Agent exceeded 60 requests per minute",
            "severity": "medium",
        })
    
    status = "ok" if not any(f["severity"] == "high" for f in findings) else "failed_policy"
    return status, findings


def get_policy_thresholds(agent_type: str) -> Dict[str, float]:
    """
    Get risk thresholds based on agent type.
    Returns dict with thresholds for blocking/flagging actions.
    """
    thresholds = {
        "general": {
            "block_threshold": 80,      # Block if risk > 80
            "flag_threshold": 60,       # Flag if risk > 60
            "confidence_minimum": 0.7   # Require 70% confidence
        },
        "financial": {
            "block_threshold": 70,      # Stricter for financial
            "flag_threshold": 50,
            "confidence_minimum": 0.85
        },
        "medical": {
            "block_threshold": 75,      # Very strict for medical
            "flag_threshold": 55,
            "confidence_minimum": 0.90
        },
        "legal": {
            "block_threshold": 75,
            "flag_threshold": 55,
            "confidence_minimum": 0.85
        },
        "technical": {
            "block_threshold": 85,      # More lenient for technical
            "flag_threshold": 65,
            "confidence_minimum": 0.75
        }
    }
    
    return thresholds.get(agent_type, thresholds["general"])


def format_policy_report(
    status: str,
    summary: Dict[str, Any],
    findings: List[Tuple[str, str, str]]
) -> str:
    """
    Format policy evaluation results as human-readable report.
    """
    lines = [f"Policy Evaluation: {status.upper()}"]
    lines.append(f"Total Checks: {summary.get('total_checks', 0)}")
    lines.append(f"Passed: {summary.get('passed', 0)}")
    lines.append(f"Failed: {summary.get('failed', 0)}")
    
    if findings:
        lines.append("\nFindings:")
        for severity, code, message in findings:
            icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "🔵"
            lines.append(f"{icon} [{severity.upper()}] {code}: {message}")
    
    return "\n".join(lines)