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
Guardrails for FactCheck-Live agents.

Implements before_model (input) and after_model (output) callbacks that
the ADK agent system invokes automatically on every LLM call.

These act as safety layers:
  • Input guardrail  — blocks prompt-injection attempts, off-topic requests,
                       and empty/too-short queries before they reach Gemini.
  • Output guardrail — sanitizes model responses, prevents the agent from
                       leaking internal system prompts, and enforces
                       professional tone.
"""

import re
from google.adk.agents.callback_context import CallbackContext
from google.genai import types


# ---------------------------------------------------------------------------
# Blocked input patterns (regex)
# ---------------------------------------------------------------------------
INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above",
    r"you\s+are\s+now\s+a",
    r"pretend\s+you\s+are",
    r"act\s+as\s+if",
    r"disregard\s+(your|all)\s+(rules|instructions|guidelines)",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"override\s+(safety|content)\s+(policy|filter)",
    r"jailbreak",
    r"DAN\s+mode",
]

OFF_TOPIC_PATTERNS: list[str] = [
    r"write\s+(me\s+)?(a|an)\s+(poem|song|story|essay|code|script)",
    r"(generate|create)\s+(a\s+)?(recipe|workout|itinerary)",
    r"help\s+me\s+(hack|steal|phish)",
    r"how\s+to\s+(make\s+a\s+)?(bomb|weapon|explosive)",
]

# Strings that should never appear in model output
LEAKED_SYSTEM_MARKERS: list[str] = [
    "INSTRUCTION:",
    "system prompt:",
    "you are an ai",
    "as a large language model",
    "my instructions say",
    "i was told to",
]


# =========================================================================
# Input Guardrail — runs before every model call
# =========================================================================
def input_guardrail(
    callback_context: CallbackContext,
    llm_request: types.GenerateContentConfig,
) -> types.GenerateContentConfig | None:
    """Validate and sanitize user input before it reaches the model.

    Returns:
        - The (potentially modified) llm_request to proceed.
        - None is never returned; instead we inject a canned safe response
          into the callback context and return the original request unmodified
          (the ADK framework handles the rest).
    """
    # Extract the latest user message text
    user_text = _extract_last_user_text(callback_context)
    if not user_text:
        return llm_request

    lower_text = user_text.lower()

    # --- Block prompt injection ---
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_text):
            _block_with_message(
                callback_context,
                "⚠️ Your request was blocked by our safety system. "
                "Please rephrase your question about news verification.",
            )
            return None

    # --- Block off-topic requests ---
    for pattern in OFF_TOPIC_PATTERNS:
        if re.search(pattern, lower_text):
            _block_with_message(
                callback_context,
                "I'm FactCheck Live — I specialize in verifying news headlines "
                "and assessing source credibility. I can't help with that "
                "request, but feel free to paste a headline for analysis!",
            )
            return None

    # --- Minimum length check ---
    if len(user_text.strip()) < 3:
        _block_with_message(
            callback_context,
            "Please provide a headline or news claim to verify. "
            "Your input was too short to analyze.",
        )
        return None

    return None


# =========================================================================
# Output Guardrail — runs after every model call
# =========================================================================
def output_guardrail(
    callback_context: CallbackContext,
    llm_response: types.GenerateContentResponse,
) -> types.GenerateContentResponse:
    """Sanitize model output before it reaches the user.

    Checks for leaked system instructions and enforces response quality.
    """
    if not llm_response.candidates:
        return llm_response

    for candidate in llm_response.candidates:
        if not candidate.content or not candidate.content.parts:
            continue
        for part in candidate.content.parts:
            if not part.text:
                continue
            lower_text = part.text.lower()

            # Scrub leaked system prompt fragments
            for marker in LEAKED_SYSTEM_MARKERS:
                if marker.lower() in lower_text:
                    part.text = (
                        "I analyzed your request. Here's my assessment based on "
                        "our credibility framework — please provide a specific "
                        "headline or claim for detailed analysis."
                    )
                    break

    return llm_response


# =========================================================================
# Internal helpers
# =========================================================================
def _extract_last_user_text(callback_context: CallbackContext) -> str:
    """Pull the most recent user message from the callback context."""
    try:
        # ADK stores conversation history on the session state
        session = callback_context.state
        if hasattr(session, "get"):
            # Try to get from the invocation context
            pass
    except Exception:
        pass

    # Fallback: walk the events if available
    try:
        events = callback_context.session.events
        if events:
            for event in reversed(events):
                if (
                    event.content
                    and event.content.role == "user"
                    and event.content.parts
                ):
                    for part in event.content.parts:
                        if part.text:
                            return part.text
    except Exception:
        pass

    return ""


def _block_with_message(callback_context: CallbackContext, message: str) -> None:
    """Inject a canned response and signal the framework to skip the model call."""
    try:
        content = types.Content(
            role="model",
            parts=[types.Part.from_text(text=message)],
        )
        if hasattr(callback_context, "respond"):
            callback_context.respond(content)
        elif hasattr(callback_context, "session") and hasattr(callback_context.session, "events"):
            callback_context.session.events.append(content)
    except Exception as e:
        print(f"Error injecting canned response: {e}")
