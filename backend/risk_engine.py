# backend/risk_engine.py
"""
Real-Time Risk Oracle for AI Agent Actions
Analyzes actions BEFORE execution to prevent disasters
"""

import json
import statistics
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict

class RiskScore:
    """Container for risk analysis results"""
    def __init__(
        self,
        score: float,  # 0-100 (0=safe, 100=dangerous)
        level: str,    # "low", "medium", "high", "critical"
        flags: List[Dict[str, Any]],
        explanation: str,
        should_block: bool,
        confidence: float  # 0-1
    ):
        self.score = score
        self.level = level
        self.flags = flags
        self.explanation = explanation
        self.should_block = should_block
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_score": self.score,
            "risk_level": self.level,
            "flags": self.flags,
            "explanation": self.explanation,
            "should_block": self.should_block,
            "confidence": self.confidence
        }

class RiskOracle:
    """
    Real-time risk analysis engine for AI agent actions.
    Uses historical patterns, statistical analysis, and rule-based checks.
    """
    
    def __init__(self):
        # Agent behavior history: agent_id -> list of past actions
        self.agent_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        
        # Agent reputation scores (learned from evaluations)
        self.agent_reputation: Dict[str, float] = defaultdict(lambda: 50.0)
        
        # Global thresholds (can be customized per agent type)
        self.thresholds = {
            "low": 30,      # 0-30: Low risk, auto-approve
            "medium": 60,   # 31-60: Medium risk, flag for review
            "high": 80,     # 61-80: High risk, require approval
            "critical": 100 # 81-100: Critical risk, auto-block
        }
        
        # Action patterns that are inherently risky
        self.risky_patterns = [
            "transfer", "delete", "drop", "execute", "admin",
            "sudo", "root", "password", "secret", "key"
        ]
        
        # Time-based risk factors
        self.business_hours = (9, 17)  # 9 AM - 5 PM
        
    def analyze_action(
        self,
        agent_id: str,
        action_data: Dict[str, Any],
        agent_type: str = "general"
    ) -> RiskScore:
        """
        Main entry point: Analyze an action and return risk assessment.
        
        Args:
            agent_id: Unique identifier for the agent
            action_data: Action payload with inputs, outputs, model info
            agent_type: Type of agent (financial, medical, etc.)
        
        Returns:
            RiskScore object with detailed analysis
        """
        flags = []
        risk_factors = []
        
        # Extract key fields
        inputs = action_data.get("inputs", {})
        outputs = action_data.get("outputs", {})
        model = action_data.get("model", "")
        
        # 1. ANOMALY DETECTION: Compare to agent's historical behavior
        anomaly_score, anomaly_flags = self._detect_anomalies(
            agent_id, action_data
        )
        flags.extend(anomaly_flags)
        risk_factors.append(anomaly_score)
        
        # 2. PATTERN MATCHING: Check for risky keywords/patterns
        pattern_score, pattern_flags = self._check_patterns(inputs, outputs)
        flags.extend(pattern_flags)
        risk_factors.append(pattern_score)
        
        # 3. MAGNITUDE ANALYSIS: Check for unusually large values
        magnitude_score, magnitude_flags = self._analyze_magnitude(
            agent_id, inputs, outputs
        )
        flags.extend(magnitude_flags)
        risk_factors.append(magnitude_score)
        
        # 4. TEMPORAL ANALYSIS: Check time-of-day risks
        temporal_score, temporal_flags = self._analyze_timing()
        flags.extend(temporal_flags)
        risk_factors.append(temporal_score)
        
        # 5. AGENT REPUTATION: Factor in past behavior
        reputation_score = self._get_reputation_risk(agent_id)
        risk_factors.append(reputation_score)
        
        # 6. TYPE-SPECIFIC RULES: Apply domain-specific checks
        type_score, type_flags = self._apply_type_rules(
            agent_type, inputs, outputs
        )
        flags.extend(type_flags)
        risk_factors.append(type_score)
        
        # Calculate weighted final score
        weights = [0.25, 0.20, 0.20, 0.10, 0.15, 0.10]  # Sum = 1.0
        final_score = sum(
            score * weight 
            for score, weight in zip(risk_factors, weights)
        )
        
        # Determine risk level and action
        risk_level = self._classify_risk(final_score)
        should_block = risk_level == "critical"
        
        # Build explanation
        explanation = self._build_explanation(
            final_score, flags, agent_id, risk_level
        )
        
        # Confidence based on amount of historical data
        confidence = self._calculate_confidence(agent_id)
        
        return RiskScore(
            score=round(final_score, 2),
            level=risk_level,
            flags=flags,
            explanation=explanation,
            should_block=should_block,
            confidence=round(confidence, 2)
        )
    
    def _detect_anomalies(
        self,
        agent_id: str,
        action_data: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Detect if this action deviates significantly from agent's normal behavior.
        Uses statistical analysis of historical patterns.
        """
        flags = []
        
        history = self.agent_history.get(agent_id, [])
        if len(history) < 3:
            # Not enough data for meaningful anomaly detection
            return 20.0, [{
                "type": "insufficient_data",
                "severity": "info",
                "message": "Limited history available for this agent"
            }]
        
        # Extract numeric values from inputs/outputs
        current_values = self._extract_numeric_values(action_data)
        historical_values = [
            self._extract_numeric_values(h) for h in history
        ]
        
        # Calculate z-scores for anomaly detection
        anomaly_score = 0.0
        for key, value in current_values.items():
            past_values = [
                h.get(key) for h in historical_values if key in h
            ]
            if len(past_values) >= 3:
                mean = statistics.mean(past_values)
                stdev = statistics.stdev(past_values) if len(past_values) > 1 else 0
                
                if stdev > 0:
                    z_score = abs((value - mean) / stdev)
                    
                    if z_score > 3:  # 3 standard deviations
                        anomaly_score += 30
                        flags.append({
                            "type": "statistical_anomaly",
                            "severity": "high",
                            "message": f"Value for '{key}' is {z_score:.1f}σ from normal (expected ~{mean:.0f}, got {value:.0f})"
                        })
                    elif z_score > 2:  # 2 standard deviations
                        anomaly_score += 15
                        flags.append({
                            "type": "unusual_value",
                            "severity": "medium",
                            "message": f"Value for '{key}' is {z_score:.1f}σ from normal"
                        })
        
        return min(anomaly_score, 100.0), flags
    
    def _check_patterns(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Check for risky keywords or patterns in the action data.
        """
        flags = []
        risk = 0.0
        
        # Convert to string for pattern matching
        text = json.dumps({"inputs": inputs, "outputs": outputs}).lower()
        
        for pattern in self.risky_patterns:
            if pattern in text:
                risk += 15
                flags.append({
                    "type": "risky_pattern",
                    "severity": "medium",
                    "message": f"Detected risky keyword: '{pattern}'"
                })
        
        # Check for potential PII
        pii_patterns = ["ssn", "social security", "credit card", "password"]
        for pattern in pii_patterns:
            if pattern in text:
                risk += 25
                flags.append({
                    "type": "pii_detected",
                    "severity": "high",
                    "message": f"Potential PII detected: '{pattern}'"
                })
        
        return min(risk, 100.0), flags
    
    def _analyze_magnitude(
        self,
        agent_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Analyze numerical magnitudes for unusually large values.
        """
        flags = []
        risk = 0.0
        
        # Extract all numeric values
        values = self._extract_numeric_values({
            "inputs": inputs,
            "outputs": outputs
        })
        
        history = self.agent_history.get(agent_id, [])
        if history:
            # Calculate historical averages
            for key, value in values.items():
                past_values = [
                    self._extract_numeric_values(h).get(key)
                    for h in history
                ]
                past_values = [v for v in past_values if v is not None]
                
                if past_values:
                    avg = statistics.mean(past_values)
                    ratio = value / avg if avg > 0 else 0
                    
                    if ratio > 10:  # 10x larger than average
                        risk += 40
                        flags.append({
                            "type": "magnitude_spike",
                            "severity": "high",
                            "message": f"Value for '{key}' is {ratio:.1f}x larger than average ({value:.0f} vs {avg:.0f})"
                        })
                    elif ratio > 5:  # 5x larger
                        risk += 20
                        flags.append({
                            "type": "elevated_magnitude",
                            "severity": "medium",
                            "message": f"Value for '{key}' is {ratio:.1f}x larger than typical"
                        })
        
        # Absolute thresholds (domain-agnostic)
        for key, value in values.items():
            if value > 1_000_000:  # Over 1 million
                risk += 20
                flags.append({
                    "type": "large_absolute_value",
                    "severity": "medium",
                    "message": f"Large value detected: {key}={value:,.0f}"
                })
        
        return min(risk, 100.0), flags
    
    def _analyze_timing(self) -> Tuple[float, List[Dict[str, str]]]:
        """
        Analyze time-of-day risk factors.
        """
        flags = []
        risk = 0.0
        
        now = datetime.now()
        hour = now.hour
        
        # Check if outside business hours
        if hour < self.business_hours[0] or hour >= self.business_hours[1]:
            risk += 15
            flags.append({
                "type": "off_hours",
                "severity": "low",
                "message": f"Action requested outside business hours ({hour}:00)"
            })
        
        # Weekend check
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            risk += 10
            flags.append({
                "type": "weekend_activity",
                "severity": "low",
                "message": "Action requested on weekend"
            })
        
        return risk, flags
    
    def _get_reputation_risk(self, agent_id: str) -> float:
        """
        Convert agent reputation (0-100, higher is better) to risk score.
        """
        reputation = self.agent_reputation.get(agent_id, 50.0)
        # Invert: high reputation = low risk
        return 100.0 - reputation
    
    def _apply_type_rules(
        self,
        agent_type: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> Tuple[float, List[Dict[str, str]]]:
        """
        Apply domain-specific rules based on agent type.
        """
        flags = []
        risk = 0.0
        
        if agent_type == "financial":
            # Check for large transactions
            amount = self._find_amount(inputs, outputs)
            if amount and amount > 10_000:
                risk += 30
                flags.append({
                    "type": "large_transaction",
                    "severity": "high",
                    "message": f"Transaction amount ${amount:,.0f} exceeds safety threshold"
                })
        
        elif agent_type == "medical":
            # Medical actions should have high confidence
            confidence = outputs.get("confidence", 1.0)
            if confidence < 0.90:
                risk += 25
                flags.append({
                    "type": "low_confidence_medical",
                    "severity": "high",
                    "message": f"Medical recommendation has low confidence: {confidence:.2%}"
                })
        
        elif agent_type == "legal":
            # Legal advice should flag speculative language
            text = json.dumps(outputs).lower()
            uncertain_terms = ["maybe", "possibly", "might", "could be"]
            if any(term in text for term in uncertain_terms):
                risk += 15
                flags.append({
                    "type": "uncertain_legal_advice",
                    "severity": "medium",
                    "message": "Legal advice contains uncertain language"
                })
        
        return risk, flags
    
    def _classify_risk(self, score: float) -> str:
        """Classify numerical risk score into level."""
        if score <= self.thresholds["low"]:
            return "low"
        elif score <= self.thresholds["medium"]:
            return "medium"
        elif score <= self.thresholds["high"]:
            return "high"
        else:
            return "critical"
    
    def _build_explanation(
        self,
        score: float,
        flags: List[Dict[str, str]],
        agent_id: str,
        level: str
    ) -> str:
        """Generate human-readable explanation of risk assessment."""
        if not flags:
            return f"Action appears safe. Risk score: {score:.0f}/100 (Agent reputation: good)"
        
        high_severity = [f for f in flags if f.get("severity") == "high"]
        medium_severity = [f for f in flags if f.get("severity") == "medium"]
        
        parts = [f"Risk assessment: {level.upper()} ({score:.0f}/100)"]
        
        if high_severity:
            parts.append(f"\n⚠️ {len(high_severity)} high-severity concern(s):")
            for flag in high_severity[:3]:  # Top 3
                parts.append(f"  • {flag['message']}")
        
        if medium_severity:
            parts.append(f"\n⚡ {len(medium_severity)} medium concern(s):")
            for flag in medium_severity[:2]:  # Top 2
                parts.append(f"  • {flag['message']}")
        
        if level == "critical":
            parts.append("\n🚫 Action BLOCKED due to critical risk level")
        elif level == "high":
            parts.append("\n⏸️ Action requires manual approval")
        
        return "\n".join(parts)
    
    def _calculate_confidence(self, agent_id: str) -> float:
        """
        Calculate confidence in risk assessment based on available data.
        More history = higher confidence.
        """
        history_count = len(self.agent_history.get(agent_id, []))
        
        if history_count == 0:
            return 0.3  # Low confidence with no history
        elif history_count < 5:
            return 0.5  # Medium-low confidence
        elif history_count < 20:
            return 0.7  # Medium-high confidence
        else:
            return 0.9  # High confidence
    
    def _extract_numeric_values(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Extract all numeric values from nested dict."""
        values = {}
        
        def extract(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    extract(v, f"{prefix}{k}_" if prefix else f"{k}_")
            elif isinstance(obj, (int, float)):
                values[prefix.rstrip("_")] = float(obj)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract(item, f"{prefix}{i}_")
        
        extract(data)
        return values
    
    def _find_amount(
        self,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> Optional[float]:
        """Find amount/value in action data (common field names)."""
        combined = {**inputs, **outputs}
        
        for key in ["amount", "value", "total", "price", "cost", "amount_usd"]:
            if key in combined:
                val = combined[key]
                if isinstance(val, (int, float)):
                    return float(val)
        
        return None
    
    # --- History Management ---
    
    def record_action(
        self,
        agent_id: str,
        action_data: Dict[str, Any]
    ):
        """Record action in agent's history for future analysis."""
        self.agent_history[agent_id].append(action_data)
        
        # Keep only last 100 actions per agent
        if len(self.agent_history[agent_id]) > 100:
            self.agent_history[agent_id] = self.agent_history[agent_id][-100:]
    
    def update_reputation(
        self,
        agent_id: str,
        evaluation: bool,
        delta: float = 5.0
    ):
        """
        Update agent reputation based on evaluation.
        Good action = increase reputation, bad = decrease.
        """
        current = self.agent_reputation[agent_id]
        
        if evaluation:  # Good action
            new_rep = min(100.0, current + delta)
        else:  # Bad action
            new_rep = max(0.0, current - delta)
        
        self.agent_reputation[agent_id] = new_rep
    
    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get statistics about an agent."""
        return {
            "action_count": len(self.agent_history.get(agent_id, [])),
            "reputation": self.agent_reputation.get(agent_id, 50.0),
            "risk_profile": self._calculate_risk_profile(agent_id)
        }
    
    def _calculate_risk_profile(self, agent_id: str) -> str:
        """Classify agent's overall risk profile."""
        rep = self.agent_reputation.get(agent_id, 50.0)
        
        if rep >= 80:
            return "trusted"
        elif rep >= 60:
            return "reliable"
        elif rep >= 40:
            return "neutral"
        elif rep >= 20:
            return "concerning"
        else:
            return "high_risk"


# Singleton instance
_oracle = None

def get_risk_oracle() -> RiskOracle:
    """Get the global risk oracle instance."""
    global _oracle
    if _oracle is None:
        _oracle = RiskOracle()
    return _oracle