# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Shared tools for FactCheck-Live sub-agents.

Each tool is a plain function with Pydantic input models, following the
google-adk tool pattern from the shopping-assistant reference.
"""

import re
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Reputable / Questionable source registries
# ---------------------------------------------------------------------------
REPUTABLE_SOURCES: list[str] = [
    "bbc", "reuters", "associated press", "ap news", "npr", "pbs", "wsj",
    "the new york times", "nytimes", "the washington post", "bloomberg",
    "the guardian", "financial times", "the verge", "techcrunch", "wired",
    # Indian & Regional
    "ndtv", "the hindu", "times of india", "indian express",
    "hindustan times", "mint", "manorama", "mathrubhumi", "asianet",
    "mediaone", "daily thanthi", "dinamalar", "puthiya thalaimurai",
]

QUESTIONABLE_SOURCES: list[str] = [
    "infowars", "breitbart", "occupy democrats", "naturalnews",
    "daily wire", "the gateway pundit", "palmer report",
    "bipartisan report",
]

# ---------------------------------------------------------------------------
# Linguistic red-flag keyword lists
# ---------------------------------------------------------------------------
CLICKBAIT_KEYWORDS: list[str] = [
    "shocking", "miracle", "you won't believe", "secret", "mind-blowing",
    "insane", "destroy", "banned", "genius", "unbelievable", "exposed",
    "truth about", "last chance", "breaking warning", "must see", "viral",
    "jaw-dropping",
]

MANIPULATIVE_KEYWORDS: list[str] = [
    "slams", "outrage", "destroyed", "owned", "humiliates", "furious",
    "meltdown", "panic", "expert says", "they don't want you to know",
]


# =========================================================================
# Tool 1 — Source Credibility Check
# =========================================================================
class SourceCheckRequest(BaseModel):
    source_name: str = Field(
        description="Name of the news source or publication to evaluate."
    )


def check_source_credibility(request: SourceCheckRequest) -> str:
    """Evaluate the credibility tier of a news source.

    Returns a structured assessment: REPUTABLE, QUESTIONABLE, or UNKNOWN,
    along with a confidence note.
    """
    source_lower = request.source_name.strip().lower()

    if any(s in source_lower for s in REPUTABLE_SOURCES):
        return (
            f"SOURCE_TIER: REPUTABLE\n"
            f"Source '{request.source_name}' is recognized as a major, "
            f"editorially-vetted news outlet with established fact-checking "
            f"standards. Credibility score bonus: +25."
        )

    if any(s in source_lower for s in QUESTIONABLE_SOURCES):
        return (
            f"SOURCE_TIER: QUESTIONABLE\n"
            f"Source '{request.source_name}' has been flagged by multiple "
            f"media-bias watchdogs for publishing misleading content. "
            f"Credibility score penalty: -30."
        )

    return (
        f"SOURCE_TIER: UNKNOWN\n"
        f"Source '{request.source_name}' is not in the verified registry. "
        f"Unable to confirm editorial standards. Mild penalty: -5."
    )


# =========================================================================
# Tool 2 — Linguistic Red-Flag Scanner
# =========================================================================
class HeadlineAnalysisRequest(BaseModel):
    headline: str = Field(
        description="The news headline text to analyze for linguistic red flags."
    )


def scan_headline_language(request: HeadlineAnalysisRequest) -> str:
    """Scan a headline for clickbait, manipulative, and sensationalist patterns.

    Returns a detailed breakdown of every detected issue with per-flag
    penalty values the Language Agent can aggregate.
    """
    headline = request.headline
    lower = headline.lower()
    flags: list[str] = []
    total_penalty = 0

    # --- Clickbait keywords ---
    found_clickbait = [kw for kw in CLICKBAIT_KEYWORDS if kw in lower]
    if found_clickbait:
        penalty = 15 * len(found_clickbait)
        total_penalty += penalty
        flags.append(
            f"CLICKBAIT_KEYWORDS ({len(found_clickbait)}): "
            f"{', '.join(found_clickbait)} → penalty: -{penalty}"
        )

    # --- Manipulative keywords ---
    found_manipulative = [kw for kw in MANIPULATIVE_KEYWORDS if kw in lower]
    if found_manipulative:
        penalty = 20 * len(found_manipulative)
        total_penalty += penalty
        flags.append(
            f"MANIPULATIVE_TONE ({len(found_manipulative)}): "
            f"{', '.join(found_manipulative)} → penalty: -{penalty}"
        )

    # --- Excessive punctuation (!!, ??, etc.) ---
    if re.search(r"[!?]{2,}", headline):
        total_penalty += 10
        flags.append("EXCESSIVE_PUNCTUATION: Multiple ! or ? detected → penalty: -10")

    # --- ALL-CAPS density ---
    alpha_chars = re.findall(r"[a-zA-Z]", headline)
    if len(alpha_chars) > 10:
        upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
        if upper_ratio > 0.30:
            total_penalty += 15
            flags.append(
                f"EXCESSIVE_CAPS: {upper_ratio:.0%} uppercase "
                f"(threshold 30%) → penalty: -15"
            )

    # --- Suspiciously short ---
    word_count = len(headline.split())
    if word_count < 4:
        total_penalty += 10
        flags.append(
            f"SHORT_HEADLINE: Only {word_count} words "
            f"(minimum 4 expected) → penalty: -10"
        )

    if not flags:
        return (
            "LINGUISTIC_SCAN: CLEAN\n"
            "No clickbait, manipulative, or anomalous patterns detected. "
            "Total penalty: 0."
        )

    report = "LINGUISTIC_SCAN: FLAGS DETECTED\n"
    report += "\n".join(f"  • {f}" for f in flags)
    report += f"\n\nTotal linguistic penalty: -{total_penalty}"
    return report


# =========================================================================
# Tool 3 — Cross-Reference Context Lookup
# =========================================================================
class ContextLookupRequest(BaseModel):
    claim: str = Field(
        description="The core factual claim extracted from the headline to cross-reference."
    )
    source: str = Field(
        default="",
        description="Optional: the originating source for additional context.",
    )


# A small deterministic knowledge base mirroring the MCP server's data
KNOWN_FACTS: dict[str, dict] = {
    # Medical & Health
    "cure cancer miracle": {
        "verdict": "Likely Fake",
        "score": 5,
        "reason": "Medical consensus states there is no single 'miracle cure' for all cancers. Such claims are unverified and potentially dangerous.",
        "flags": ["Medical Misinformation", "Unverified Claim"],
    },
    "vaccine microchip tracking": {
        "verdict": "Likely Fake",
        "score": 2,
        "reason": "No injectable microchip technology exists at vaccine-needle scale. Debunked by FDA, WHO, and independent fact-checkers globally.",
        "flags": ["Debunked Conspiracy", "Health Misinformation"],
    },
    "5g covid cause": {
        "verdict": "Likely Fake",
        "score": 3,
        "reason": "Debunked by WHO, CDC, and every major health authority. Radio frequency waves cannot create or transmit biological viruses.",
        "flags": ["Debunked Conspiracy", "Health Misinformation"],
    },
    "ivermectin covid cure": {
        "verdict": "Likely Fake",
        "score": 8,
        "reason": "Large-scale clinical trials (TOGETHER, ACTIV-6) found no meaningful benefit of ivermectin for COVID-19 treatment.",
        "flags": ["Medical Misinformation", "Debunked Treatment"],
    },
    "drinking bleach cure virus": {
        "verdict": "Likely Fake",
        "score": 1,
        "reason": "Ingesting bleach is extremely dangerous and can be fatal. No legitimate medical authority recommends this.",
        "flags": ["Dangerous Misinformation", "Health Hazard"],
    },
    # Conspiracy Theories
    "alien ufo abduction": {
        "verdict": "Likely Fake",
        "score": 10,
        "reason": "No credible scientific agency has confirmed extraterrestrial abductions or visitations on Earth.",
        "flags": ["Conspiracy Theory", "Lack of Evidence"],
    },
    "flat earth proof": {
        "verdict": "Likely Fake",
        "score": 5,
        "reason": "Contradicts centuries of empirical evidence and satellite imagery. No credible scientific institution supports this claim.",
        "flags": ["Debunked Conspiracy", "Anti-Science"],
    },
    "nasa moon fake studio": {
        "verdict": "Likely Fake",
        "score": 5,
        "reason": "The Apollo moon landings are historically documented and scientifically verified with physical evidence including lunar samples.",
        "flags": ["Debunked Conspiracy"],
    },
    "chemtrails spray population": {
        "verdict": "Likely Fake",
        "score": 4,
        "reason": "Contrails are condensation from jet exhaust. No credible evidence supports deliberate chemical spraying from aircraft.",
        "flags": ["Debunked Conspiracy", "Pseudoscience"],
    },
    # Political Misinformation
    "election fraud stolen millions": {
        "verdict": "Likely Fake",
        "score": 10,
        "reason": "Claims of widespread election fraud involving millions of votes have been dismissed by over 60 courts and confirmed false by DOJ, CISA, and bipartisan officials.",
        "flags": ["Debunked Claim", "Legally Adjudicated"],
    },
    "deep state shadow government": {
        "verdict": "Likely Fake",
        "score": 15,
        "reason": "The 'deep state' conspiracy lacks credible evidence. Government bureaucracy is not equivalent to a coordinated shadow government.",
        "flags": ["Conspiracy Theory", "Politically Charged"],
    },
    # Climate & Environment
    "climate change hoax": {
        "verdict": "Likely Fake",
        "score": 8,
        "reason": "Overwhelming scientific consensus (IPCC, NASA, NOAA) confirms climate change is real and primarily driven by human activities.",
        "flags": ["Scientific Consensus Violation", "Misinformation"],
    },
    "climate change report temperature": {
        "verdict": "Likely Real",
        "score": 85,
        "reason": "Climate reporting from scientific institutions is regularly published and verifiable through peer-reviewed data.",
        "flags": ["Scientifically Verified"],
    },
    # Technology (Verifiable)
    "apple iphone release": {
        "verdict": "Likely Real",
        "score": 85,
        "reason": "Tech companies like Apple regularly release new models of their flagship devices. Product announcements are easily verifiable.",
        "flags": ["Standard Industry News"],
    },
    "google ai launch model": {
        "verdict": "Likely Real",
        "score": 82,
        "reason": "Major tech companies regularly announce AI products. Verify through official press releases and company blogs.",
        "flags": ["Tech Industry News", "Verifiable"],
    },
    "data breach million hack": {
        "verdict": "Uncertain",
        "score": 60,
        "reason": "Data breaches are common but specific claims require verification through official company statements or security advisories.",
        "flags": ["Requires Verification", "Cybersecurity"],
    },
    # Economics & Finance
    "inflation fed interest rates": {
        "verdict": "Likely Real",
        "score": 90,
        "reason": "Economic news regarding inflation and Federal Reserve interest rates are standard, verifiable events published by official sources.",
        "flags": ["Economic News", "Verifiable"],
    },
    "stock market crash imminent": {
        "verdict": "Uncertain",
        "score": 30,
        "reason": "Market crash predictions are extremely common and rarely accurate. Exercise caution with alarmist financial predictions.",
        "flags": ["Speculative", "Financial Fearmongering"],
    },
    "crypto guaranteed profit returns": {
        "verdict": "Likely Fake",
        "score": 8,
        "reason": "No investment offers guaranteed returns. Claims of guaranteed crypto profits are hallmarks of financial scams.",
        "flags": ["Financial Scam", "Fraudulent Claim"],
    },
    # Geopolitics & International
    "war nuclear imminent launch": {
        "verdict": "Uncertain",
        "score": 20,
        "reason": "Nuclear threat claims require verification from official defense and intelligence sources. Alarmist framing is common in misinformation.",
        "flags": ["Requires Official Verification", "Alarmist"],
    },
    "sanctions trade agreement bilateral": {
        "verdict": "Likely Real",
        "score": 80,
        "reason": "Trade agreements and sanctions are official government actions, typically documented in public records.",
        "flags": ["Government Record", "Verifiable"],
    },
    # Science & Research
    "study published journal research": {
        "verdict": "Likely Real",
        "score": 75,
        "reason": "Peer-reviewed research published in recognized journals has undergone academic scrutiny, though individual studies should be considered alongside the broader literature.",
        "flags": ["Academic Source", "Peer Reviewed"],
    },
    "scientists discover cure all": {
        "verdict": "Likely Fake",
        "score": 5,
        "reason": "Claims of a universal cure for all diseases contradict the fundamental complexity of medicine and biology.",
        "flags": ["Extraordinary Claim", "Medical Misinformation"],
    },
}


def cross_reference_claim(request: ContextLookupRequest) -> str:
    """Cross-reference a factual claim against the internal knowledge base.

    Searches for keyword matches in the KNOWN_FACTS registry and returns
    structured verification data if a match is found.
    """
    claim_lower = request.claim.lower()

    for keyword, data in KNOWN_FACTS.items():
        if keyword in claim_lower:
            return (
                f"CROSS_REFERENCE: MATCH FOUND\n"
                f"  Keyword: {keyword}\n"
                f"  Verdict: {data['verdict']}\n"
                f"  Score: {data['score']}\n"
                f"  Reason: {data['reason']}\n"
                f"  Flags: {', '.join(data['flags'])}"
            )

    return (
        "CROSS_REFERENCE: NO MATCH\n"
        "The claim does not match any entry in the internal knowledge base. "
        "Recommend the orchestrator rely on source credibility and "
        "linguistic analysis for the final verdict."
    )
