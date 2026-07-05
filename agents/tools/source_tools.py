"""
Source Credibility Analysis Tools
Evaluates news source trustworthiness against curated databases of
reputable and questionable news organizations worldwide.

Used by: Source Credibility Agent
"""

from pydantic import BaseModel, Field


# ─── Curated Source Credibility Databases ────────────────────────────────────
# Trust scores are on a 0-100 scale based on editorial standards,
# fact-checking track record, and journalistic integrity assessments.

REPUTABLE_SOURCES: dict[str, int] = {
    # International Wire Services & Legacy Broadsheets
    "reuters": 95,
    "associated press": 95,
    "ap news": 95,
    "bbc": 92,
    "npr": 90,
    "pbs": 90,
    "the new york times": 88,
    "nytimes": 88,
    "the washington post": 87,
    "the guardian": 86,
    "financial times": 90,
    "bloomberg": 89,
    "wsj": 88,
    "the wall street journal": 88,
    "the economist": 91,
    "al jazeera": 82,
    "deutsche welle": 84,
    "france 24": 83,
    "abc news": 82,
    "cbs news": 82,
    "nbc news": 82,
    "cnn": 78,
    # Technology
    "the verge": 80,
    "techcrunch": 80,
    "wired": 82,
    "ars technica": 85,
    "mit technology review": 88,
    "engadget": 76,
    # Science & Academic
    "nature": 96,
    "science": 95,
    "scientific american": 88,
    "new scientist": 85,
    "the lancet": 95,
    "national geographic": 86,
    # Indian & Regional
    "ndtv": 78,
    "the hindu": 82,
    "times of india": 75,
    "indian express": 80,
    "hindustan times": 76,
    "mint": 80,
    "the print": 78,
    "scroll.in": 77,
    "the wire": 76,
    "manorama": 75,
    "mathrubhumi": 74,
}

QUESTIONABLE_SOURCES: dict[str, int] = {
    "infowars": 8,
    "breitbart": 15,
    "naturalnews": 5,
    "the gateway pundit": 10,
    "occupy democrats": 18,
    "daily wire": 25,
    "palmer report": 20,
    "bipartisan report": 22,
    "zero hedge": 18,
    "epoch times": 20,
    "newsmax": 25,
    "oann": 15,
    "world net daily": 10,
    "RT": 20,
    "sputnik": 15,
}


# ─── Tool Input Schema ──────────────────────────────────────────────────────

class CheckSourceRequest(BaseModel):
    """Input schema for the source credibility check tool."""

    source: str = Field(
        description="The name of the news source to evaluate for credibility."
    )


# ─── Tool Implementation ────────────────────────────────────────────────────

def check_source_credibility(request: CheckSourceRequest) -> str:
    """Evaluate a news source's credibility against curated trust databases.

    Checks the provided source name against databases of reputable and
    questionable news organizations. Returns a structured credibility report
    including trust score, classification, and assessment narrative.

    Args:
        request: Contains the source name to evaluate.

    Returns:
        A formatted credibility report string with score and classification.
    """
    source_lower = request.source.lower().strip()

    # Check reputable sources (partial match for flexibility)
    for name, trust_score in REPUTABLE_SOURCES.items():
        if name in source_lower or source_lower in name:
            return (
                f"SOURCE CREDIBILITY REPORT:\n"
                f"  Source: {request.source}\n"
                f"  Classification: REPUTABLE\n"
                f"  Trust Score: {trust_score}/100\n"
                f"  Assessment: This is a well-established news organization with "
                f"professional editorial standards, fact-checking processes, and "
                f"a documented track record of journalistic integrity.\n"
            )

    # Check questionable sources
    for name, trust_score in QUESTIONABLE_SOURCES.items():
        if name.lower() in source_lower or source_lower in name.lower():
            return (
                f"SOURCE CREDIBILITY REPORT:\n"
                f"  Source: {request.source}\n"
                f"  Classification: QUESTIONABLE\n"
                f"  Trust Score: {trust_score}/100\n"
                f"  Assessment: This source has a documented history of publishing "
                f"misleading, hyper-partisan, or unverified content. Multiple "
                f"fact-checking organizations have flagged it for inaccuracies.\n"
            )

    # Unknown source — not in either database
    return (
        f"SOURCE CREDIBILITY REPORT:\n"
        f"  Source: {request.source}\n"
        f"  Classification: UNKNOWN\n"
        f"  Trust Score: 40/100\n"
        f"  Assessment: This source is not present in our credibility database. "
        f"Unable to verify editorial standards or journalistic integrity. "
        f"Recommend cross-referencing this story with established news outlets.\n"
    )
