"""
Linguistic Analysis Tools
Detects manipulation, sensationalism, clickbait patterns, and linguistic
red flags in news headlines through multi-phase pattern analysis.

Used by: Language Analysis Agent
"""

import re
from pydantic import BaseModel, Field


# ─── Detection Keyword Databases ────────────────────────────────────────────

CLICKBAIT_KEYWORDS: list[str] = [
    "shocking", "miracle", "you won't believe", "secret", "mind-blowing",
    "insane", "destroy", "banned", "genius", "unbelievable", "exposed",
    "truth about", "last chance", "breaking warning", "must see", "viral",
    "jaw-dropping", "game changer", "revolutionary", "exclusive leak",
    "doctors hate", "one weird trick", "this changes everything",
]

MANIPULATIVE_KEYWORDS: list[str] = [
    "slams", "outrage", "destroyed", "owned", "humiliates", "furious",
    "meltdown", "panic", "expert says", "they don't want you to know",
    "wake up", "sheeple", "mainstream media", "cover-up", "bombshell",
    "rips apart", "eviscerates", "decimates", "obliterates",
]

# Regex patterns for absolute/universal claims that are rarely accurate
ABSOLUTE_CLAIM_PATTERNS: list[str] = [
    r"\ball\b.*\bcure[ds]?\b",
    r"\bproven\b.*\b(fake|hoax|lie)\b",
    r"\b100\s*%\b",
    r"\bguaranteed\b",
    r"\bno one\b.*\btalking\b",
    r"\beveryone\b.*\b(knows?|agrees?)\b",
    r"\bonce and for all\b",
    r"\bfinally exposed\b",
]


# ─── Tool Input Schema ──────────────────────────────────────────────────────

class AnalyzeLanguageRequest(BaseModel):
    """Input schema for headline linguistic analysis."""

    title: str = Field(
        description="The news headline text to analyze for manipulation patterns."
    )


# ─── Tool Implementation ────────────────────────────────────────────────────

def analyze_headline_language(request: AnalyzeLanguageRequest) -> str:
    """Analyze a headline for clickbait, manipulation, and linguistic red flags.

    Performs six-phase analysis covering:
    1. Sensationalist/clickbait keyword detection
    2. Manipulative framing language
    3. Punctuation anomalies (excessive ! or ?)
    4. Capitalization density (ALL CAPS detection)
    5. Headline length validation
    6. Absolute/universal claim patterns

    Args:
        request: Contains the headline text to analyze.

    Returns:
        A formatted linguistic analysis report with score and detailed findings.
    """
    title = request.title
    lower_title = title.lower()
    flags: list[str] = []
    deductions = 0

    # ── Phase 1: Clickbait keyword detection ──
    found_clickbait = [kw for kw in CLICKBAIT_KEYWORDS if kw in lower_title]
    if found_clickbait:
        deductions += 15 * len(found_clickbait)
        flags.append(
            f"Clickbait keywords detected: {', '.join(found_clickbait)}"
        )

    # ── Phase 2: Manipulative framing detection ──
    found_manipulative = [kw for kw in MANIPULATIVE_KEYWORDS if kw in lower_title]
    if found_manipulative:
        deductions += 20 * len(found_manipulative)
        flags.append(
            f"Manipulative framing: {', '.join(found_manipulative)}"
        )

    # ── Phase 3: Punctuation anomaly analysis ──
    excessive_punct = re.findall(r"[!?]{2,}", title)
    if excessive_punct:
        deductions += 10
        flags.append("Excessive punctuation (multiple ! or ? in sequence)")

    # ── Phase 4: Capitalization density ──
    alpha_chars = re.findall(r"[a-zA-Z]", title)
    upper_chars = re.findall(r"[A-Z]", title)
    if len(alpha_chars) > 10:
        cap_ratio = len(upper_chars) / len(alpha_chars)
        if cap_ratio > 0.5:
            deductions += 20
            flags.append(
                f"Excessive capitalization ({cap_ratio:.0%} uppercase — "
                f"possible ALL CAPS shouting)"
            )
        elif cap_ratio > 0.3:
            deductions += 10
            flags.append(
                f"High capitalization density ({cap_ratio:.0%} uppercase)"
            )

    # ── Phase 5: Headline length validation ──
    word_count = len(title.split())
    if word_count < 4:
        deductions += 10
        flags.append(f"Suspiciously short headline ({word_count} words)")
    elif word_count > 30:
        deductions += 5
        flags.append(f"Unusually long headline ({word_count} words)")

    # ── Phase 6: Absolute claim patterns ──
    for pattern in ABSOLUTE_CLAIM_PATTERNS:
        if re.search(pattern, lower_title, re.IGNORECASE):
            deductions += 15
            flags.append("Contains absolute or universal claim")
            break

    # Calculate language score (100 = perfectly clean, neutral language)
    language_score = max(0, min(100, 100 - deductions))

    if not flags:
        flags.append("No linguistic red flags detected — headline uses neutral, factual tone")

    # Build formatted report
    report = (
        f"LINGUISTIC ANALYSIS REPORT:\n"
        f"  Headline: \"{title}\"\n"
        f"  Language Score: {language_score}/100\n"
        f"  Total Deductions: -{deductions} points\n"
        f"  Flags Detected: {len(flags)}\n"
        f"\n"
        f"  Detailed Findings:\n"
    )
    for i, flag in enumerate(flags, 1):
        report += f"    {i}. {flag}\n"

    return report
