# Architecture & Developer Notes
**Project:** FactCheck Analytics Local Engine  
**Module:** Agent Tools & Interoperability  

## Architectural Overview
This system demonstrates the transition from monolithic software development to Agentic Engineering. By utilizing standardized protocols, specifically the Model Context Protocol (MCP), the application establishes a machine-readable, robust connection between localized algorithms and external knowledge bases.

### 1. Model Context Protocol (MCP) Integration
- **Concept**: MCP serves as a standardized "socket" replacing bespoke REST wrappers and custom JSON parsers.
- **Implementation**: The system implements an MCP server (`mcp-server.js`) connected via `StdioServerTransport` to the primary Express application (`server.js`).
- **Benefit**: Reduces integration complexity and facilitates seamless decoupling of the local heuristic engine from the data-retrieval layer.

### 2. Verification Fallback Mechanism
The primary verification route attempts to match headlines against the structured MCP knowledge base via the `verify_fact` tool call. If the MCP response is inconclusive or execution fails, the system automatically falls back to the **Local Heuristic Engine**.

### 3. Local Heuristic Engine Ruleset
The local engine scores headlines (0-100 base scale) using the following parameters:
- **Source Verification**: Awards points for reputable sources; penalizes questionable domains.
- **Linguistic Analysis**: Applies severe penalties for the presence of predefined sensationalist (clickbait) and manipulative keywords.
- **Syntax Anomaly Detection**: Penalizes excessive punctuation (e.g., multiple exclamation points) and over-capitalization (density > 30%).
- **Length Validation**: Flags suspiciously short headlines.

## Extensibility
Future iterations of this application are designed to integrate with external LLM providers (e.g., Gemini API) via the MCP transport layer to perform advanced contextual reasoning when local heuristics yield an "Uncertain" verdict.
