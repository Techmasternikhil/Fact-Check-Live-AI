"""
FactCheck Live — Multi-Agent AI Misinformation Detection System

A multi-agent system built with Google's Agent Development Kit (ADK) that
coordinates three specialist verification agents to analyze news headline
credibility in real-time.

Agents:
    1. Source Credibility Agent — Evaluates news source trustworthiness
    2. Language Analysis Agent — Detects manipulation and clickbait patterns
    3. Context Verification Agent — AI-powered factual plausibility reasoning

Architecture:
    FactCheck Commander (Orchestrator)
    ├── Source Agent + check_source_credibility tool
    ├── Language Agent + analyze_headline_language tool
    └── Context Agent + verify_claim_with_ai tool (Gemini API)

Usage:
    from agents import orchestrator_agent, app

    # Use with ADK playground:
    #   agents-cli playground

    # Use programmatically:
    #   from agents.orchestrator import orchestrator_agent
"""

from agents.orchestrator import orchestrator_agent, app, root_agent

__all__ = ["orchestrator_agent", "app", "root_agent"]
