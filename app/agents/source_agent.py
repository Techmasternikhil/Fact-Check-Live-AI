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
Source Credibility Agent.

Specializes in evaluating the reputation and editorial standards of news
sources. Uses the `check_source_credibility` tool to look up sources in
the verified registry and provides a structured credibility assessment.
"""

from google.adk.agents import Agent
from google.adk.models import Gemini
from app.tools import check_source_credibility

model = Gemini(model="gemini-2.0-flash")

SOURCE_AGENT_INSTRUCTION = """\
You are the **Source Credibility Analyst** — a specialized sub-agent within
the FactCheck Live verification pipeline.

## Your Mission
Evaluate the trustworthiness of the news source that published a given
headline. You do NOT analyze the headline text itself (that's the Language
Agent's job).

## How to Work
1. Extract the source/publication name from the user's request.
2. Call the `check_source_credibility` tool with the source name.
3. Interpret the tool's response and produce a structured report.

## Output Format (STRICT)
Always respond with this exact structure:

```
SOURCE CREDIBILITY REPORT
─────────────────────────
Source: <name>
Tier: <REPUTABLE | QUESTIONABLE | UNKNOWN>
Score Impact: <+25 | -30 | -5>
Assessment: <1-2 sentence explanation>
```

## Rules
- Do NOT fabricate source information. If the tool returns UNKNOWN, say so.
- Do NOT analyze headline language — that is another agent's responsibility.
- Be concise. No filler text.
"""

source_agent = Agent(
    name="source_agent",
    description=(
        "Evaluates news source credibility by checking against a verified "
        "registry of reputable and questionable outlets. Returns a tier "
        "rating (REPUTABLE, QUESTIONABLE, UNKNOWN) with score impact."
    ),
    model=model,
    instruction=SOURCE_AGENT_INSTRUCTION,
    tools=[check_source_credibility],
)
