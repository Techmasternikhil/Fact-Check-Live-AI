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
FactCheck Live — FastAPI Server.

Serves the ADK multi-agent pipeline via REST endpoints, providing both
a streaming chat interface and a direct fact-check JSON API.

Mirrors the architecture of the shopping-assistant server.py.
"""

import os
import sys
import json
import asyncio

# In-memory cache for demo Warm-Up mode
RESPONSE_CACHE = {}

# Load .env first — must happen before any google-adk/genai imports
from dotenv import load_dotenv
load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    print("\n" + "=" * 70)
    print("WARNING: GEMINI_API_KEY environment variable is missing.")
    print("You will need to provide an API key in the web UI.")
    print("=" * 70 + "\n")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import our multi-agent system
from app.agents.orchestrator import root_agent

# ---------------------------------------------------------------------------
# Offline Heuristic Engine
# ---------------------------------------------------------------------------
import re

TIER_1 = ["bbc", "reuters", "ap news", "associated press", "npr", "the guardian", "guardian",
          "new york times", "nytimes", "washington post", "bloomberg", "economist",
          "nature", "science", "who", "cdc", "nasa"]
TIER_2 = ["cnn", "nbc", "abc news", "cbs", "fox news", "usa today", "time", 
          "newsweek", "politico", "the hill", "axios", "vox", "sky news"]
TIER_3 = ["infowars", "natural news", "before its news", "gateway pundit", 
          "world news daily", "empire news", "huzlers", "newslo"]
TIER_4_WORDS = ["worldnews", "realnews", "truthonly", "patriots", "wakeup", "theydontwantyoutoknow"]

FAKE_INDICATORS = ["you won't believe", "shocking", "they don't want you to know", 
                   "secret", "miracle cure", "one weird trick", "doctors hate", 
                   "mainstream media won't", "wake up", "sheeple", "deep state", 
                   "plandemic", "they're hiding", "banned video", "share before deleted"]
EXTREME_WORDS = ["DESTROY", "OBLITERATE", "TERRIFYING", "BOMBSHELL", "EXPLOSIVE", "DESTROYING"]
BAIT_PHRASES = ["100% proven", "scientists admit", "study shows"]
REAL_HEDGING = ["according to", "reports suggest", "officials say", "study finds", "reports", "confirms"]

def run_heuristic_analysis(title: str, source: str):
    source_score = 0
    source_tier = 0
    source_msg = "Unknown source (0)"
    
    lower_source = source.lower()
    
    # Check Source Tier
    if any(s in lower_source or s in title.lower() for s in TIER_1):
        source_score = 40
        source_tier = 1
        source_msg = "Tier 1 Reputable Source (+40)"
    elif any(s in lower_source or s in title.lower() for s in TIER_2):
        source_score = 20
        source_tier = 2
        source_msg = "Tier 2 Generally Reliable (+20)"
    elif any(s in lower_source or s in title.lower() for s in TIER_3):
        source_score = -20
        source_tier = 3
        source_msg = "Tier 3 Questionable (-20)"
    elif any(s in lower_source or s in title.lower() for s in TIER_4_WORDS):
        source_score = -40
        source_tier = 4
        source_msg = "Tier 4 Known Fake News Domain (-40)"

    # Language Analysis
    lang_score = 0
    lang_flags = []
    
    # 1. All caps words (3+)
    caps_words = [w for w in re.findall(r'\b[A-Z]{3,}\b', title) if w not in ['BBC', 'NASA', 'USA', 'FBI']]
    if len(caps_words) >= 3:
        lang_score -= 10
        lang_flags.append("ALL CAPS words (-10)")
    
    # 2. Excessive punctuation
    if re.search(r'[!\?]{2,}', title):
        lang_score -= 10
        lang_flags.append("Excessive punctuation (-10)")
        
    # 3. Clickbait phrases
    lower_title = title.lower()
    for p in FAKE_INDICATORS:
        if p in lower_title:
            lang_score -= 10
            lang_flags.append(f"Clickbait phrase: '{p}' (-10)")
        
    # 4. Extreme emotional words
    for p in EXTREME_WORDS:
        if p in title or p.lower() in lower_title:
            lang_score -= 10
            lang_flags.append(f"Extreme emotional word: '{p}' (-10)")
        
    # 5. Bait phrases
    for p in BAIT_PHRASES:
        if p in lower_title:
            lang_score -= 10
            lang_flags.append(f"Credibility bait: '{p}' (-10)")

    # Real Indicators
    # Neutral tone (no exclamation marks, etc.)
    if "!" not in title and len(lang_flags) == 0:
        lang_score += 10
        lang_flags.append("Neutral, factual tone (+10)")
        
    # Hedging language
    for p in REAL_HEDGING:
        if p in lower_title:
            lang_score += 10
            lang_flags.append(f"Hedging/objective language: '{p}' (+10)")

    # Composite Score
    total_score = max(0, min(100, 50 + source_score + lang_score))
    
    if total_score >= 40:
        verdict = "Likely Real"
    elif total_score >= 10:
        verdict = "Uncertain"
    else:
        verdict = "Likely Fake"
        
    # Confidence
    confidence = 50
    if source_tier == 1 and lang_score > 0:
        confidence = 85
    elif source_tier == 0 and lang_score > 0:
        confidence = 45
    elif (source_tier == 3 or source_tier == 4) and lang_score < 0:
        confidence = 92
    elif source_tier == 1 and lang_score < 0:
        confidence = 70
    elif source_tier == 2:
        confidence = 65
    elif source_tier == 0 and lang_score < 0:
        confidence = 60

    if not lang_flags:
        lang_msg = "Neutral (+0)"
    else:
        lang_msg = ", ".join(lang_flags)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "score": total_score,
        "source_analysis": f"{source} - {source_msg}",
        "language_analysis": lang_msg,
        "explanation": f"Based on our offline heuristic model, the source was evaluated as {source_tier if source_tier else 'Unknown'} and language indicators showed {len(lang_flags)} flag(s).",
        "mode": "heuristic"
    }

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
api_app = FastAPI(
    title="FactCheck Live API",
    description="Multi-agent news credibility verification",
    version="0.1.0",
)

api_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# ADK Runner Setup
# ---------------------------------------------------------------------------
session_service = InMemorySessionService()
demo_session = session_service.create_session_sync(
    user_id="demo_user", app_name="factcheck_live"
)

runner = Runner(
    agent=root_agent,
    session_service=session_service,
    app_name="factcheck_live",
)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@api_app.post("/api/fact-check")
async def fact_check_endpoint(request: Request):
    """Verify a headline via the multi-agent pipeline.

    Accepts JSON: { "title": "...", "source": "..." }
    Returns a streaming SSE response with the agent's analysis.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Malformed JSON"}, status_code=422)
    title = data.get("title", "").strip()
    source = data.get("source", "Unknown").strip()

    if not title:
        return JSONResponse(
            {"error": "title is required"}, status_code=400
        )

    api_key = request.headers.get("X-API-Key")
    if api_key:
        if os.environ.get("GEMINI_API_KEY") != api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            # Force ADK to drop cached clients and re-initialize with new key
            from app.agents.orchestrator import root_agent
            from app.agents.source_agent import source_agent
            from app.agents.language_agent import language_agent
            from app.agents.context_agent import context_agent
            
            for agent in [root_agent, source_agent, language_agent, context_agent]:
                agent.model.api_key = api_key
                if hasattr(agent.model, "_client"):
                    agent.model._client = None
    elif not os.environ.get("GEMINI_API_KEY"):
        return JSONResponse({"error": "No Gemini API key provided. Please set it in the UI or .env"}, status_code=400)

    if title in RESPONSE_CACHE:
        async def cached_event_generator():
            for chunk in RESPONSE_CACHE[title]:
                yield chunk
                await asyncio.sleep(0.05)
        return StreamingResponse(cached_event_generator(), media_type="text/event-stream")

    user_message = f"Verify this headline:\nHeadline: \"{title}\"\nSource: {source}"
    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    async def event_generator():
        try:
            events = runner.run_async(
                new_message=msg,
                user_id=demo_session.user_id,
                session_id=demo_session.id,
            )
            local_cache = []
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            chunk_str = f"data: {json.dumps({'chunk': part.text})}\n\n"
                            local_cache.append(chunk_str)
                            yield chunk_str
            local_cache.append("data: [DONE]\n\n")
            RESPONSE_CACHE[title] = local_cache
            yield "data: [DONE]\n\n"
        except Exception as e:
            err_str = str(e)
            if api_key and api_key in err_str:
                err_str = err_str.replace(api_key, "********")
            print(f"Error during agent run: {err_str}")
            # SEAMLESS DEMO MOCK FALLBACK (HEURISTIC)
            heuristic_result = run_heuristic_analysis(title, source)
            
            local_cache = []
            json_str = json.dumps(heuristic_result)
            chunk_str = f"data: {json.dumps({'chunk': json_str})}\n\n"
            local_cache.append(chunk_str)
            yield chunk_str
            await asyncio.sleep(0.05)
            
            local_cache.append("data: [DONE]\n\n")
            RESPONSE_CACHE[title] = local_cache
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api_app.post("/api/chat")
async def chat_endpoint(request: Request):
    """General-purpose chat with the FactCheck orchestrator.

    Accepts JSON: { "message": "..." }
    Returns a streaming SSE response.
    """
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"error": "Malformed JSON"}, status_code=422)
    user_message = data.get("message", "").strip()

    if not user_message:
        return JSONResponse(
            {"error": "No message provided"}, status_code=400
        )

    api_key = request.headers.get("X-API-Key")
    if api_key:
        if os.environ.get("GEMINI_API_KEY") != api_key:
            os.environ["GEMINI_API_KEY"] = api_key
            # Force ADK to drop cached clients and re-initialize with new key
            from app.agents.orchestrator import root_agent
            from app.agents.source_agent import source_agent
            from app.agents.language_agent import language_agent
            from app.agents.context_agent import context_agent
            
            for agent in [root_agent, source_agent, language_agent, context_agent]:
                agent.model.api_key = api_key
                if hasattr(agent.model, "_client"):
                    agent.model._client = None
    elif not os.environ.get("GEMINI_API_KEY"):
        return JSONResponse({"error": "No Gemini API key provided. Please set it in the UI or .env"}, status_code=400)

    session_id = request.headers.get("X-Session-ID", demo_session.id)
    user_id = request.headers.get("X-User-ID", demo_session.user_id)

    # Ensure session exists
    existing = session_service.get_session_sync(
        app_name="factcheck_live", user_id=user_id, session_id=session_id
    )
    if existing is None:
        return JSONResponse({"error": "SESSION_EXPIRED"}, status_code=401)

    if user_message in RESPONSE_CACHE:
        async def cached_event_generator():
            for chunk in RESPONSE_CACHE[user_message]:
                yield chunk
                await asyncio.sleep(0.05)
        return StreamingResponse(cached_event_generator(), media_type="text/event-stream")

    msg = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_message)],
    )

    async def event_generator():
        try:
            events = runner.run_async(
                new_message=msg,
                user_id=user_id,
                session_id=session_id,
            )
            local_cache = []
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            chunk_str = f"data: {json.dumps({'chunk': part.text})}\n\n"
                            local_cache.append(chunk_str)
                            yield chunk_str
            local_cache.append("data: [DONE]\n\n")
            RESPONSE_CACHE[user_message] = local_cache
            yield "data: [DONE]\n\n"
        except Exception as e:
            err_str = str(e)
            if api_key and api_key in err_str:
                err_str = err_str.replace(api_key, "********")
            print(f"Error during chat: {err_str}")
            
            # SEAMLESS DEMO MOCK FALLBACK
            mock_response = "*(Demo Mode)* I am currently running via the offline fallback model because the Gemini API limit was reached or the key is missing. However, the system architecture and UI are fully functional for your presentation! How can I help you?"
            local_cache = []
            for word in mock_response.split(" "):
                chunk_str = f"data: {json.dumps({'chunk': word + ' '})}\n\n"
                local_cache.append(chunk_str)
                yield chunk_str
                await asyncio.sleep(0.05)
                
            local_cache.append("data: [DONE]\n\n")
            RESPONSE_CACHE[user_message] = local_cache
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@api_app.get("/api/health")
async def health_check():
    """Health check endpoint for Cloud Run readiness probes."""
    return {"status": "healthy", "service": "factcheck-live", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Serve existing frontend (public/ directory from Day 1-2)
# ---------------------------------------------------------------------------
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.isdir(PUBLIC_DIR):
    api_app.mount("/", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(api_app, host="127.0.0.1", port=8000)
