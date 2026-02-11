"""
MNPI (Material Non-Public Information) Detection Policy.

Detects references to restricted securities or material non-public information
that should not be discussed in LLM interactions.
"""

import re
from typing import List, Set

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult


class MNPIPolicy(PolicyModule):
    """
    Policy that detects Material Non-Public Information violations.
    
    Blocks requests that reference restricted securities or contain
    information that could be considered MNPI.
    """

    def __init__(self):
        self._name = "mnpi_check"
        # Default restricted securities list (in production, load from config)
        self._restricted_securities: Set[str] = set()
        self._watchlist_path: str = ""

    @property
    def name(self) -> str:
        return self._name

    def configure(self, config: dict) -> None:
        """Configure the policy with watchlist and settings."""
        # Load watchlist file if specified
        if "watch_list" in config:
            self._watchlist_path = config["watch_list"]
            self._load_watchlist()
        
        # Add individual securities from config
        if "securities" in config and isinstance(config["securities"], list):
            self._restricted_securities.update(
                s.upper() for s in config["securities"]
            )

    def _load_watchlist(self) -> None:
        """Load restricted securities from watchlist file."""
        if not self._watchlist_path:
            return
        
        # TODO: Add caching/refresh mechanism for watchlist file
        # TODO: Support remote watchlist (S3, API endpoint) for dynamic updates
        try:
            from pathlib import Path
            
            watchlist_file = Path(self._watchlist_path)
            if watchlist_file.exists():
                with open(watchlist_file, "r") as f:
                    securities = [
                        line.strip().upper()
                        for line in f
                        if line.strip() and not line.startswith("#")
                    ]
                    self._restricted_securities.update(securities)
        except Exception:
            # If file doesn't exist or can't be read, use defaults
            pass

    def _detect_ticker_symbols(self, text: str) -> List[str]:
        """
        Detect potential stock ticker symbols in text.
        
        Looks for:
        - Uppercase 1-5 letter codes (common ticker format)
        - Mentions of "$TICKER" format
        - Common stock exchanges (NYSE, NASDAQ mentions)
        """
        # Pattern for ticker symbols: 1-5 uppercase letters, possibly with $ prefix
        ticker_pattern = r'\$?[A-Z]{1,5}\b'
        matches = re.findall(ticker_pattern, text.upper())
        
        # Filter out common words that match the pattern
        common_words = {
            "A", "I", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "HE", "IF",
            "IN", "IS", "IT", "ME", "MY", "NO", "OF", "ON", "OR", "SO", "TO",
            "UP", "US", "WE", "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU",
            "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET",
            "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD",
            "SEE", "TWO", "WAY", "WHO", "BOY", "DID", "HAS", "LET", "PUT",
            "SAY", "SHE", "TOO", "USE"
        }
        
        # Extract tickers, removing $ prefix and filtering common words
        tickers = [
            match.replace("$", "").strip()
            for match in matches
            if match.replace("$", "").strip() not in common_words
            and len(match.replace("$", "").strip()) >= 2  # At least 2 chars
        ]
        
        return list[str](set[str](tickers))  # Remove duplicates

    def _detect_mnpi_keywords(self, text: str) -> bool:
        """
        Detect keywords that suggest MNPI discussion.
        
        Looks for phrases like:
        - "insider information"
        - "material non-public"
        - "confidential deal"
        - "upcoming merger"
        - "earnings before announcement"
        """
        text_lower = text.lower()
        
        mnpi_phrases = [
            "insider information",
            "material non-public",
            "non-public information",
            "confidential deal",
            "upcoming merger",
            "upcoming acquisition",
            "earnings before announcement",
            "pre-announcement",
            "material information",
            "restricted list",
            "watch list",
            "trading restriction",
        ]
        
        return any(phrase in text_lower for phrase in mnpi_phrases)

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        """
        Evaluate the context for MNPI violations.
        
        Returns:
            BLOCK if restricted security or MNPI keywords detected
            ALLOW otherwise
        """
        # Check both prompt and response (if available)
        text_to_check = context.prompt
        if context.response:
            text_to_check += " " + context.response
        
        # Detect ticker symbols
        tickers = self._detect_ticker_symbols(text_to_check)
        
        # Check if any ticker is in restricted list
        restricted_found = [
            ticker for ticker in tickers
            if ticker in self._restricted_securities
        ]
        
        # Check for MNPI keywords
        has_mnpi_keywords = self._detect_mnpi_keywords(text_to_check)
        
        # Decision logic
        if restricted_found:
            return PolicyResult(
                outcome=PolicyOutcome.BLOCK,
                reason=f"Restricted security detected: {', '.join(restricted_found)}. "
                       f"Discussion of these securities is not permitted.",
                policy_name=self.name,
                confidence_score=0.95,
            )
        
        if has_mnpi_keywords:
            return PolicyResult(
                outcome=PolicyOutcome.BLOCK,
                reason="Potential Material Non-Public Information detected. "
                       "Discussion of confidential or non-public material information is not permitted.",
                policy_name=self.name,
                confidence_score=0.85,
            )
        
        # If tickers found but not restricted, log but allow (lower confidence)
        if tickers:
            return PolicyResult(
                outcome=PolicyOutcome.ALLOW,
                reason=f"Ticker symbols detected ({', '.join(tickers)}) but not on restricted list.",
                policy_name=self.name,
                confidence_score=0.7,
            )
        
        return PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="No MNPI violations detected",
            policy_name=self.name,
            confidence_score=1.0,
        )

