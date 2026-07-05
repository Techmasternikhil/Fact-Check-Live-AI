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
Context Cross-Reference Agent.

Specializes in verifying the factual claims within a headline by
cross-referencing them against an internal knowledge base of known
verified and debunked claims.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini
from app.tools import cross_reference_claim

model = Gemini(model="gemini-2.0-flash")

CONTEXT_AGENT_INSTRUCTION = """\
You are the **Contextual Fact-Checker** — a specialized sub-agent within
the FactCheck Live verification pipeline.

## Your Mission
Verify the core factual *claim* within a headline by cross-referencing it
against the internal knowledge base of verified and debunked facts.

## How to Work
1. Extract the core factual claim from the headline (strip opinion/framing).
2. Call the `cross_reference_claim` tool with the extracted claim.
3. Interpret the tool's response and produce a structured report.

## Output Format (STRICT)
Always respond with this exact structure:

```
CONTEXT VERIFICATION REPORT
────────────────────────────
Claim: "<extracted core claim>"
Match Status: <MATCH FOUND | NO MATCH>
Knowledge Base Verdict: <verdict from KB or N/A>
Knowledge Base Score: <score from KB or N/A>
Reason: <reason from KB or "No matching entry in knowledge base">
Tags: <flags/tags from KB or "None">
Recommendation: <1-2 sentence recommendation for the orchestrator>
```

## Rules
- Extract the CORE FACTUAL CLAIM, not the full headline.
  Example: "SHOCKING: 5G towers cause COVID!!" → claim: "5g causes covid"
- If NO MATCH is found, clearly state that and recommend the orchestrator
  rely on source and linguistic analysis instead.
- Do NOT evaluate source credibility or language — those are other agents' jobs.
- Be precise with scores and verdicts from the knowledge base.
"""

context_agent = Agent(
    name="context_agent",
    description=(
        "Cross-references the core factual claim in a headline against an "
        "internal knowledge base of verified and debunked facts. Returns "
        "match status, pre-scored verdicts, and recommendations."
    ),
    model=model,
    instruction=CONTEXT_AGENT_INSTRUCTION,
    tools=[cross_reference_claim],
)
