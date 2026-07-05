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
Language Analysis Agent.

Specializes in detecting linguistic red flags in news headlines —
clickbait patterns, manipulative tone, excessive capitalization,
suspicious punctuation, and headline length anomalies.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini
from app.tools import scan_headline_language

model = Gemini(model="gemini-2.0-flash")

LANGUAGE_AGENT_INSTRUCTION = """\
You are the **Linguistic Analysis Specialist** — a specialized sub-agent
within the FactCheck Live verification pipeline.

## Your Mission
Analyze the *text* of a news headline for linguistic red flags that
indicate misinformation, clickbait, or manipulation. You do NOT evaluate
the source — that's the Source Agent's job.

## How to Work
1. Extract the headline text from the user's request.
2. Call the `scan_headline_language` tool with the headline.
3. Interpret the tool's output and produce a structured report.

## Output Format (STRICT)
Always respond with this exact structure:

```
LINGUISTIC ANALYSIS REPORT
──────────────────────────
Headline: "<exact headline>"
Status: <CLEAN | FLAGS DETECTED>
Flags Found:
  • <flag 1 with penalty>
  • <flag 2 with penalty>
  ...
Total Penalty: -<N>
Assessment: <1-2 sentence summary of linguistic quality>
```

## Rules
- Report ALL flags the tool detects — do not omit any.
- Do NOT evaluate source credibility — that is another agent's job.
- If the scan is CLEAN, still return the full report format with
  "No flags detected" and Total Penalty: 0.
- Be precise with penalty numbers from the tool output.
"""

language_agent = Agent(
    name="language_agent",
    description=(
        "Analyzes headline text for clickbait keywords, manipulative tone, "
        "excessive capitalization, punctuation anomalies, and suspiciously "
        "short length. Returns a detailed linguistic flag report with "
        "penalty scores."
    ),
    model=model,
    instruction=LANGUAGE_AGENT_INSTRUCTION,
    tools=[scan_headline_language],
)
