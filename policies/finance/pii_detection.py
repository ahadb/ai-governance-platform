"""
PII (Personally Identifiable Information) Detection and Redaction Policy.

Detects PII in prompts/responses and redacts it before allowing the request
to proceed.
"""

import re
from typing import Dict, List, Tuple

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult


class PIIDetectionPolicy(PolicyModule):
    """
    Policy that detects and redacts Personally Identifiable Information.
    
    Detects:
    - Email addresses
    - Phone numbers
    - Social Security Numbers (SSN)
    - Credit card numbers
    - Bank account numbers (basic patterns)
    
    Returns REDACT outcome with modified content.
    """

    def __init__(self):
        self._name = "pii_detection"
        self._redact_emails = True
        self._redact_phones = True
        self._redact_ssn = True
        self._redact_credit_cards = True
        self._redact_bank_accounts = True
        
        # Counter for generating unique redaction tokens
        self._redaction_counter = 0

    @property
    def name(self) -> str:
        return self._name

    def configure(self, config: dict) -> None:
        """Configure what types of PII to detect and redact."""
        self._redact_emails = config.get("redact_emails", True)
        self._redact_phones = config.get("redact_phones", True)
        self._redact_ssn = config.get("redact_ssn", True)
        self._redact_credit_cards = config.get("redact_credit_cards", True)
        self._redact_bank_accounts = config.get("redact_bank_accounts", True)

    def _generate_redaction_token(self, pii_type: str) -> str:
        """Generate a unique redaction token."""
        self._redaction_counter += 1
        return f"[REDACTED:{pii_type}:ref_{self._redaction_counter:04d}]"

    def _detect_emails(self, text: str) -> List[Tuple[str, str]]:
        """Detect email addresses. Returns list of (email, token) tuples."""
        if not self._redact_emails:
            return []
        
        # Email pattern: word@domain.tld
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        return [
            (email, self._generate_redaction_token("EMAIL"))
            for email in emails
        ]

    def _detect_phone_numbers(self, text: str) -> List[Tuple[str, str]]:
        """Detect phone numbers. Returns list of (phone, token) tuples."""
        if not self._redact_phones:
            return []
        
        # Phone patterns: (123) 456-7890, 123-456-7890, 123.456.7890, +1-123-456-7890
        phone_patterns = [
            r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International
        ]
        
        phones = []
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        # Remove duplicates
        unique_phones = list(set(phones))
        
        return [
            (phone, self._generate_redaction_token("PHONE"))
            for phone in unique_phones
        ]

    def _detect_ssn(self, text: str) -> List[Tuple[str, str]]:
        """Detect Social Security Numbers. Returns list of (ssn, token) tuples."""
        if not self._redact_ssn:
            return []
        
        # SSN pattern: XXX-XX-XXXX or XXX XX XXXX
        ssn_pattern = r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b'
        ssns = re.findall(ssn_pattern, text)
        
        # Filter out obvious non-SSNs (like dates, zip codes with 5 digits)
        # Basic heuristic: SSNs usually have dashes/spaces
        filtered_ssns = [
            ssn for ssn in ssns
            if '-' in ssn or ' ' in ssn or '.' in ssn
        ]
        
        return [
            (ssn, self._generate_redaction_token("SSN"))
            for ssn in filtered_ssns
        ]

    def _detect_credit_cards(self, text: str) -> List[Tuple[str, str]]:
        """Detect credit card numbers. Returns list of (card, token) tuples."""
        if not self._redact_credit_cards:
            return []
        
        # Credit card pattern: 13-19 digits, possibly with spaces/dashes
        # More specific: 4 groups of 4 digits
        card_pattern = r'\b\d{4}[-.\s]?\d{4}[-.\s]?\d{4}[-.\s]?\d{4}\b'
        cards = re.findall(card_pattern, text)
        
        return [
            (card, self._generate_redaction_token("CREDIT_CARD"))
            for card in cards
        ]

    def _detect_bank_accounts(self, text: str) -> List[Tuple[str, str]]:
        """Detect bank account numbers (basic pattern). Returns list of (account, token) tuples."""
        if not self._redact_bank_accounts:
            return []
        
        # Bank account pattern: 8-17 digits (varies by bank)
        # Look for "account number" or "routing number" context
        account_pattern = r'\b(?:account|routing|acct|routing\s+number|account\s+number)[\s:]*\d{8,17}\b'
        accounts = re.findall(account_pattern, text, re.IGNORECASE)
        
        # Extract just the number part
        number_pattern = r'\d{8,17}'
        account_numbers = []
        for match in accounts:
            numbers = re.findall(number_pattern, match)
            account_numbers.extend(numbers)
        
        return [
            (account, self._generate_redaction_token("BANK_ACCOUNT"))
            for account in account_numbers
        ]

    def _redact_pii(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Detect and redact all PII in text.
        
        Returns:
            Tuple of (redacted_text, redaction_tokens_dict)
        """
        redacted_text = text
        redaction_tokens: Dict[str, str] = {}
        
        # Detect all PII types
        all_detections = []
        all_detections.extend(self._detect_emails(text))
        all_detections.extend(self._detect_phone_numbers(text))
        all_detections.extend(self._detect_ssn(text))
        all_detections.extend(self._detect_credit_cards(text))
        all_detections.extend(self._detect_bank_accounts(text))
        
        # Replace each PII with its token
        for original, token in all_detections:
            # Escape special regex characters in original
            escaped_original = re.escape(original)
            redacted_text = re.sub(escaped_original, token, redacted_text)
            redaction_tokens[token] = original
        
        return redacted_text, redaction_tokens

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        """
        Evaluate the context for PII and redact if found.
        
        Returns:
            REDACT if PII detected (with modified content)
            ALLOW if no PII detected
        """
        # Check prompt
        prompt_redacted, prompt_tokens = self._redact_pii(context.prompt)
        
        # Check response if available
        response_redacted = None
        response_tokens: Dict[str, str] = {}
        if context.response:
            response_redacted, response_tokens = self._redact_pii(context.response)
        
        # Combine all redaction tokens
        all_tokens = {**prompt_tokens, **response_tokens}
        
        # If PII was detected and redacted
        if all_tokens:
            # Build modified content
            modified_content = prompt_redacted
            if response_redacted:
                modified_content += "\n\n" + response_redacted
            
            return PolicyResult(
                outcome=PolicyOutcome.REDACT,
                reason=f"PII detected and redacted: {len(all_tokens)} item(s) found",
                modified_content=modified_content,
                policy_name=self.name,
                confidence_score=0.9,
                redaction_tokens=all_tokens,
            )
        
        # No PII detected
        return PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="No PII detected",
            policy_name=self.name,
            confidence_score=1.0,
        )

