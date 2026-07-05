"""
AI Context Verification Tools
Uses Gemini API for advanced contextual claim reasoning that goes beyond
pattern matching — evaluating scientific consistency, logical plausibility,
and historical context of news headlines.

Used by: Context Verification Agent
"""

import json
import os
from pydantic import BaseModel, Field


# ─── Lazy-loaded GenAI Client ────────────────────────────────────────────────
# Initialized on first use to avoid import-time failures when the API key
# is not yet available in the environment.

_genai_client = None


def _get_genai_client():
    """Lazily initialize the Google GenAI client."""
    global _genai_client
    if _genai_client is None:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


# ─── Fact-Checking System Prompt ─────────────────────────────────────────────

FACT_CHECK_SYSTEM_PROMPT = """You are an expert fact-checker and media literacy analyst.
Your task is to evaluate the factual plausibility of a news headline.

Analyze the claim from these perspectives:
1. **Scientific/Factual Consistency**: Does the claim align with established scientific 
   knowledge or verified facts?
2. **Logical Plausibility**: Is the claim logically coherent? Are there logical fallacies?
3. **Historical Context**: Does similar reporting exist from credible outlets? Is this 
   type of event plausible given what we know?
4. **Red Flags**: Are there signs of satire, parody, misattribution, or fabrication?

IMPORTANT: You must respond with ONLY a valid JSON object — no markdown fences, no 
extra text — with these exact fields:
{
  "plausibility_score": <integer 0-100>,
  "assessment": "<one of: PLAUSIBLE, QUESTIONABLE, IMPLAUSIBLE>",
  "reasoning": "<2-3 sentence explanation>",
  "red_flags": ["<list of specific concerns, if any>"]
}"""


# ─── Tool Input Schema ──────────────────────────────────────────────────────

class VerifyClaimRequest(BaseModel):
    """Input schema for AI-powered claim verification."""

    title: str = Field(
        description="The news headline to verify for factual plausibility."
    )
    source: str = Field(
        default="Unknown",
        description="The news source that published the headline.",
    )


# ─── Tool Implementation ────────────────────────────────────────────────────

def verify_claim_with_ai(request: VerifyClaimRequest) -> str:
    """Use Gemini AI to perform contextual reasoning about a headline's plausibility.

    Makes a direct Gemini API call with a specialized fact-checking system prompt.
    The AI evaluates scientific consistency, logical coherence, historical context,
    and potential red flags — capabilities that pure pattern matching cannot provide.

    This is the "brain" of the verification system — the tool that adds genuine
    AI reasoning beyond deterministic heuristics.

    Args:
        request: Contains the headline and source to verify.

    Returns:
        A formatted AI verification report with plausibility score and reasoning.
    """
    try:
        client = _get_genai_client()

        user_prompt = (
            f"Evaluate this news headline for factual plausibility:\n"
            f"Headline: \"{request.title}\"\n"
            f"Source: {request.source}\n\n"
            f"Provide your analysis as a JSON object."
        )

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=user_prompt,
            config={
                "system_instruction": FACT_CHECK_SYSTEM_PROMPT,
                "temperature": 0.2,
                "max_output_tokens": 500,
            },
        )

        response_text = response.text.strip()

        # Clean potential markdown code fence wrapping from the response
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines).strip()

        # Parse the structured JSON response
        try:
            result = json.loads(response_text)
            score = result.get("plausibility_score", 50)
            assessment = result.get("assessment", "UNKNOWN")
            reasoning = result.get("reasoning", "No reasoning provided.")
            red_flags = result.get("red_flags", [])

            flags_display = ", ".join(red_flags) if red_flags else "None detected"

            return (
                f"AI CONTEXT VERIFICATION REPORT:\n"
                f"  Headline: \"{request.title}\"\n"
                f"  Source: {request.source}\n"
                f"  Plausibility Score: {score}/100\n"
                f"  Assessment: {assessment}\n"
                f"  Reasoning: {reasoning}\n"
                f"  Red Flags: {flags_display}\n"
            )

        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw AI response as-is
            return (
                f"AI CONTEXT VERIFICATION REPORT:\n"
                f"  Headline: \"{request.title}\"\n"
                f"  Source: {request.source}\n"
                f"  AI Analysis (unstructured): {response_text}\n"
            )

    except Exception as e:
        # Graceful degradation — the system continues with the other two agents
        return (
            f"AI CONTEXT VERIFICATION REPORT:\n"
            f"  Headline: \"{request.title}\"\n"
            f"  Status: VERIFICATION UNAVAILABLE\n"
            f"  Reason: AI service error — {str(e)}\n"
            f"  Fallback: Rely on source credibility and linguistic analysis.\n"
        )
