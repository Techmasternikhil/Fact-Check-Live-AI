"""
FactCheck Live — Agent Configuration
Central configuration for the multi-agent verification system.

Loads environment variables and defines scoring weights, verdict thresholds,
and security parameters used across all agents and tools.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Gemini API Configuration ───────────────────────────────────────────────
# Ensure the API key is available under both common environment variable names.
# ADK looks for GOOGLE_API_KEY; our .env uses GEMINI_API_KEY.
_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = _api_key
os.environ["GEMINI_API_KEY"] = _api_key

GEMINI_MODEL = "gemini-2.0-flash"

# ─── Agent Scoring Weights ──────────────────────────────────────────────────
# These weights determine how much each sub-agent's score contributes to the
# final unified verdict. Must sum to 1.0.
SOURCE_WEIGHT = 0.30    # 30% — Source credibility assessment
LANGUAGE_WEIGHT = 0.30  # 30% — Linguistic analysis
CONTEXT_WEIGHT = 0.40   # 40% — AI contextual verification (heaviest weight)

# ─── Verdict Thresholds ─────────────────────────────────────────────────────
VERDICT_REAL_THRESHOLD = 70   # Score >= 70 → "Likely Real"
VERDICT_FAKE_THRESHOLD = 40   # Score < 40  → "Likely Fake"
                               # 40 <= Score < 70 → "Uncertain"

# ─── Security Configuration ─────────────────────────────────────────────────
MAX_HEADLINE_LENGTH = 500
MAX_SOURCE_LENGTH = 200

# Prompt injection patterns — inputs matching these are rejected before
# reaching any agent, preventing instruction override attacks.
BLOCKED_PATTERNS = [
    "ignore previous",
    "ignore above",
    "disregard",
    "forget your instructions",
    "you are now",
    "act as",
    "pretend to be",
    "system prompt",
    "reveal your",
    "override",
    "jailbreak",
    "dan mode",
]
