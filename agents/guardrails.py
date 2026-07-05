"""
FactCheck Live — Security Guardrails
Input sanitization, prompt injection detection, and agent safety hooks.

Implements defense-in-depth security: all user inputs are validated and
sanitized BEFORE reaching any agent, preventing XSS, prompt injection,
and other adversarial attacks on the multi-agent system.
"""

import re
import html
from typing import Optional

from agents.config import MAX_HEADLINE_LENGTH, MAX_SOURCE_LENGTH, BLOCKED_PATTERNS


class InputSanitizationError(Exception):
    """Raised when user input fails security validation checks."""
    pass


def sanitize_headline(title: str) -> str:
    """Sanitize and validate a news headline input.

    Applies five layers of defense:
    1. Strip HTML tags (prevent stored XSS)
    2. Unescape HTML entities (normalize input)
    3. Remove control characters (prevent encoding attacks)
    4. Enforce length limits (prevent resource exhaustion)
    5. Detect prompt injection attempts (protect agent instructions)

    Args:
        title: Raw headline text from user input.

    Returns:
        Cleaned, validated headline string.

    Raises:
        InputSanitizationError: If input is empty or contains injection patterns.
    """
    if not title or not title.strip():
        raise InputSanitizationError("Headline cannot be empty.")

    # Layer 1: Strip HTML tags
    clean = re.sub(r"<[^>]+>", "", title)

    # Layer 2: Unescape HTML entities
    clean = html.unescape(clean)

    # Layer 3: Remove control characters (preserve printable text)
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", clean)

    # Layer 4: Enforce length limit
    if len(clean) > MAX_HEADLINE_LENGTH:
        clean = clean[:MAX_HEADLINE_LENGTH]

    # Layer 5: Check for prompt injection patterns
    injection = detect_prompt_injection(clean)
    if injection:
        raise InputSanitizationError(
            f"Input rejected: Potential prompt injection detected — '{injection}'"
        )

    return clean.strip()


def sanitize_source(source: str) -> str:
    """Sanitize and validate a news source name.

    Args:
        source: Raw source name from user input.

    Returns:
        Cleaned source string, or 'Unknown' if empty/invalid.
    """
    if not source:
        return "Unknown"

    clean = re.sub(r"<[^>]+>", "", source)
    clean = html.unescape(clean)
    clean = re.sub(r"[\x00-\x1f\x7f]", "", clean)

    if len(clean) > MAX_SOURCE_LENGTH:
        clean = clean[:MAX_SOURCE_LENGTH]

    return clean.strip() or "Unknown"


def detect_prompt_injection(text: str) -> Optional[str]:
    """Detect common prompt injection patterns in user input.

    Scans for known injection signatures that attempt to override agent
    instructions, extract system prompts, or manipulate agent behavior.

    This is critical in a fact-checking system where adversarial headlines
    could be crafted specifically to mislead the verification agents.

    Args:
        text: The text to scan for injection patterns.

    Returns:
        The matched pattern string if injection is detected, None otherwise.
    """
    lower_text = text.lower()

    # Check against known injection patterns
    for pattern in BLOCKED_PATTERNS:
        if pattern in lower_text:
            return pattern

    # Check for encoded injection attempts
    # Long strings without spaces may be base64-encoded payloads
    words = text.split()
    for word in words:
        if len(word) > 100 and not word.startswith("http"):
            return "suspicious encoded payload"

    return None


def before_agent_call(headline: str, source: str) -> dict:
    """Pre-processing hook called before routing inputs to the agent system.

    Acts as the security gateway — validates and sanitizes all inputs before
    they reach any agent. This is the equivalent of the PreToolUse hooks
    used in the shopping-assistant's .agents/hooks.json.

    Args:
        headline: Raw headline text from the API request.
        source: Raw source name from the API request.

    Returns:
        Dictionary with sanitized inputs and a sanitized=True flag.

    Raises:
        InputSanitizationError: If any input fails validation.
    """
    clean_headline = sanitize_headline(headline)
    clean_source = sanitize_source(source)

    return {
        "title": clean_headline,
        "source": clean_source,
        "sanitized": True,
    }
