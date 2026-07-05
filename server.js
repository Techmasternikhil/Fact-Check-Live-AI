/*
 * Copyright (c) 2026 MyCompany LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import express from 'express';
import Parser from 'rss-parser';
import { fileURLToPath } from 'url';
import path from 'path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import rateLimit from 'express-rate-limit';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const parser = new Parser();
const PORT = 3000;

/** Python ADK backend URL (started separately with uvicorn) */
const ADK_BACKEND_URL = process.env.ADK_BACKEND_URL || 'http://127.0.0.1:8000';

app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

const apiLimiter = rateLimit({
  windowMs: 1 * 60 * 1000, // 1 minute
  max: 10,
  message: { error: 'Too many requests from this IP, please try again later.' }
});

/**
 * MCP Client Initialization (v2.0)
 * Connects to the enhanced knowledge base with 3 tools:
 * verify_fact, analyze_source, get_claim_context
 */
const transport = new StdioClientTransport({
  command: 'node',
  args: [path.join(__dirname, 'mcp-server.js')]
});

const mcpClient = new Client({
  name: 'factcheck-app',
  version: '2.0.0',
}, {
  capabilities: {}
});

mcpClient.connect(transport).then(() => {
  console.log('✅ Connected to MCP Knowledge Base Server v2.0');
}).catch(err => {
  console.error('❌ Failed to connect to MCP Server:', err);
});

/**
 * News Feed API Endpoint
 * Fetches and aggregates news headlines from external RSS feeds.
 */
app.get('/api/news', async (req, res) => {
  try {
    const { search, topic, limit = 10, hl = 'en-US', gl = 'US' } = req.query;

    // SECRET DEVELOPER TRICK: Inject fake news for testing
    if (search === 'TEST FAKE NEWS') {
      return res.json({
        title: "Mock Fake News Feed",
        items: [
          {
            title: "SHOCKING!!! DOCTORS HATE THIS ONE WEIRD TRICK!!! They don't want you to know about this miracle cure!",
            source: "infowars",
            link: "#",
            pubDate: new Date().toISOString()
          },
          {
            title: "BOMBSHELL: Deep state DESTROYING the economy — mainstream media won't report this EXPLOSIVE banned video. Wake up sheeple!",
            source: "natural news",
            link: "#",
            pubDate: new Date().toISOString()
          }
        ]
      });
    }

    let feedUrl = `https://news.google.com/rss?hl=${hl}&gl=${gl}&ceid=${gl}:${hl.split('-')[0]}`;
    if (search && search.trim()) {
      const query = encodeURIComponent(search.trim());
      feedUrl = `https://news.google.com/rss/search?q=${query}&hl=${hl}&gl=${gl}&ceid=${gl}:${hl.split('-')[0]}`;
    } else if (topic && topic.trim()) {
      const topicName = encodeURIComponent(topic.trim().toUpperCase());
      feedUrl = `https://news.google.com/news/rss/headlines/section/topic/${topicName}?hl=${hl}&gl=${gl}&ceid=${gl}:${hl.split('-')[0]}`;
    }

    const feed = await parser.parseURL(feedUrl);
    const items = feed.items.slice(0, parseInt(limit, 10)).map(item => ({
      title: item.title,
      link: item.link,
      pubDate: item.pubDate,
      source: item.source?.title || extractSource(item.title),
    }));

    res.json({ title: feed.title, items });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * Enhanced Fact-Check API (Phase 2)
 * Now uses all 3 MCP tools in a multi-stage pipeline:
 *   1. verify_fact     — knowledge base headline matching
 *   2. analyze_source  — source credibility registry lookup
 *   3. get_claim_context — broader context retrieval
 * Falls back to local heuristics only if all MCP checks are inconclusive.
 */
const reputableSources = [
  'bbc', 'reuters', 'associated press', 'ap news', 'npr', 'pbs', 'wsj',
  'the new york times', 'nytimes', 'the washington post', 'bloomberg',
  'the guardian', 'financial times', 'the verge', 'techcrunch', 'wired',
  // Indian & Regional
  'ndtv', 'the hindu', 'times of india', 'indian express', 'hindustan times', 'mint',
  'manorama', 'mathrubhumi', 'asianet', 'mediaone', 'matrubhumi',
  'daily thanthi', 'dinamalar', 'dinakaran', 'puthiya thalaimurai', 'sun news'
];

const questionableSources = [
  'infowars', 'breitbart', 'occupy democrats', 'naturalnews', 'daily wire',
  'the gateway pundit', 'palmer report', 'bipartisan report'
];

const clickbaitKeywords = [
  'shocking', 'miracle', "you won't believe", 'secret', 'mind-blowing',
  'insane', 'destroy', 'banned', 'genius', 'unbelievable', 'exposed', 'truth about',
  'last chance', 'breaking warning', 'must see', 'viral', 'jaw-dropping'
];

const manipulativeKeywords = [
  'slams', 'outrage', 'destroyed', 'owned', 'humiliates', 'furious',
  'meltdown', 'panic', 'expert says', "they don't want you to know"
];

app.post('/api/fact-check', apiLimiter, async (req, res) => {
  try {
    const { title, source, customSources = [], customKeywords = [] } = req.body;
    if (!title) return res.status(400).json({ error: 'title is required' });
    if (title.length > 2000) return res.status(413).json({ error: 'Payload Too Large: headline exceeds 2000 characters' });

    /**
     * Stage 1: MCP Knowledge Base — verify_fact
     */
    try {
      const mcpResult = await mcpClient.callTool({
        name: 'verify_fact',
        arguments: { title, source }
      });

      if (mcpResult?.content?.[0]?.text) {
        const mcpData = JSON.parse(mcpResult.content[0].text);
        if (mcpData.matchFound) {
          // Enrich with source analysis from new analyze_source tool
          let sourceInfo = null;
          try {
            const sourceResult = await mcpClient.callTool({
              name: 'analyze_source',
              arguments: { source: source || 'unknown' }
            });
            if (sourceResult?.content?.[0]?.text) {
              sourceInfo = JSON.parse(sourceResult.content[0].text);
            }
          } catch (_) { /* Source lookup is optional */ }

          setTimeout(() => {
            res.json({
              score: mcpData.score,
              verdict: mcpData.verdict,
              reason: mcpData.reason,
              flags: mcpData.flags,
              category: mcpData.category || 'general',
              severity: mcpData.severity || 'medium',
              confidence: mcpData.confidence || 80,
              sourceAnalysis: sourceInfo,
              engine: 'mcp'
            });
          }, 600);
          return;
        }
      }
    } catch (err) {
      console.error('MCP verify_fact failed, continuing:', err.message);
    }

    /**
     * Stage 2: MCP Source Analysis — analyze_source
     * Even if headline didn't match KB, we can still assess the source.
     */
    let mcpSourceData = null;
    try {
      const sourceResult = await mcpClient.callTool({
        name: 'analyze_source',
        arguments: { source: source || 'unknown' }
      });
      if (sourceResult?.content?.[0]?.text) {
        mcpSourceData = JSON.parse(sourceResult.content[0].text);
      }
    } catch (err) {
      console.error('MCP analyze_source failed:', err.message);
    }

    /**
     * Stage 3: MCP Claim Context — get_claim_context
     */
    let mcpContext = null;
    try {
      const contextResult = await mcpClient.callTool({
        name: 'get_claim_context',
        arguments: { claim: title }
      });
      if (contextResult?.content?.[0]?.text) {
        mcpContext = JSON.parse(contextResult.content[0].text);
      }
    } catch (err) {
      console.error('MCP get_claim_context failed:', err.message);
    }

    /**
     * Stage 4: Local Heuristics (enhanced with MCP source data)
     */
    let score = 50;
    const flags = [];
    const lowerTitle = title.toLowerCase();
    const lowerSource = (source || '').toLowerCase();

    const activeReputableSources = [...reputableSources, ...customSources.map(s => s.toLowerCase())];
    const activeClickbaitKeywords = [...clickbaitKeywords, ...customKeywords.map(k => k.toLowerCase())];

    // Use MCP source data if available, otherwise fall back to local lists
    if (mcpSourceData?.found) {
      score += mcpSourceData.scoreImpact;
      flags.push(`Source: ${mcpSourceData.credibility} (${mcpSourceData.tier})`);
    } else {
      const isReputable = activeReputableSources.some(s => s && lowerSource.includes(s));
      const isQuestionable = questionableSources.some(s => lowerSource.includes(s));

      if (isReputable) {
        score += 25;
        flags.push('Reputable Source');
      } else if (isQuestionable) {
        score -= 30;
        flags.push('Questionable Source');
      } else {
        score -= 5;
        flags.push('Unknown Source');
      }
    }

    // Clickbait analysis
    const usedClickbait = activeClickbaitKeywords.filter(k => k && lowerTitle.includes(k));
    if (usedClickbait.length > 0) {
      score -= (15 * usedClickbait.length);
      flags.push('Sensationalist Language');
    }

    // Manipulative tone
    const usedManipulative = manipulativeKeywords.filter(k => lowerTitle.includes(k));
    if (usedManipulative.length > 0) {
      score -= (20 * usedManipulative.length);
      flags.push('Manipulative Tone');
    }

    // Punctuation anomalies
    if ((title.match(/[!?]{2,}/) || []).length > 0) {
      score -= 10;
      flags.push('Excessive Punctuation');
    }

    // Capitalization density
    const upperCount = (title.match(/[A-Z]/g) || []).length;
    const alphaCount = (title.match(/[a-zA-Z]/g) || []).length;
    if (alphaCount > 10 && (upperCount / alphaCount) > 0.3) {
      score -= 15;
      flags.push('Excessive Capitalization');
    }

    // Short headline
    const wordCount = title.split(/\s+/).length;
    if (wordCount < 4) {
      score -= 10;
      flags.push('Suspiciously Short Title');
    }

    // If MCP context found related misinformation entries, adjust
    if (mcpContext?.contextFound && mcpContext.entries) {
      const fakeCount = mcpContext.entries.filter(e => e.verdict === 'Likely Fake').length;
      if (fakeCount > 0) {
        score -= (5 * fakeCount);
        flags.push(`Related Misinformation (${fakeCount} KB entries)`);
      }
    }

    // Clamp
    score = Math.max(0, Math.min(100, score));

    let verdict, reason;
    if (score >= 70) {
      verdict = 'Likely Real';
      reason = 'Headline uses factual, neutral tone and originates from a recognizable or reputable source.';
    } else if (score >= 40) {
      verdict = 'Uncertain';
      reason = 'Some signs of sensationalism or unverified source origin. Cross-check recommended.';
    } else {
      verdict = 'Likely Fake';
      reason = 'High indicators of clickbait, manipulative language, or very low source credibility.';
    }

    setTimeout(() => {
      res.json({
        score, verdict, reason,
        flags: flags.slice(0, 5),
        sourceAnalysis: mcpSourceData,
        contextMatches: mcpContext?.totalRelated || 0,
        engine: mcpSourceData?.found ? 'mcp+heuristics' : 'heuristics',
      });
    }, 600);

  } catch (err) {
    console.error('Fact-check error:', err.message);
    res.status(500).json({ error: err.message });
  }
});


/**
 * ADK Agent Bridge Endpoint (Phase 2)
 * Proxies requests to the Python ADK multi-agent backend.
 * The frontend can call this to use the full AI pipeline.
 */
app.post('/api/verify', async (req, res) => {
  try {
    const { title, source } = req.body;
    if (!title) return res.status(400).json({ error: 'title is required' });

    const apiKey = req.headers['x-api-key'];
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const response = await fetch(`${ADK_BACKEND_URL}/api/fact-check`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ title, source }),
    });

    if (!response.ok) {
      throw new Error(`ADK backend returned ${response.status}`);
    }

    // Stream the SSE response back to the client
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
    res.end();

  } catch (err) {
    console.error('ADK proxy error:', err.message);
    // If ADK backend is not running, fall through to local fact-check
    res.status(503).json({
      error: 'AI agent backend is not running. Use /api/fact-check for local analysis.',
      fallback: '/api/fact-check',
    });
  }
});


/**
 * Chat Endpoint
 * Proxies requests to the Python ADK chat backend.
 */
app.post('/api/chat', apiLimiter, async (req, res) => {
  try {
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: 'message is required' });

    const apiKey = req.headers['x-api-key'];
    const headers = { 'Content-Type': 'application/json' };
    if (apiKey) headers['X-API-Key'] = apiKey;

    const response = await fetch(`${ADK_BACKEND_URL}/api/chat`, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`ADK chat backend returned ${response.status}`);
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(decoder.decode(value, { stream: true }));
    }
    res.end();

  } catch (err) {
    console.error('ADK chat proxy error:', err.message);
    res.status(503).json({ error: 'Chat backend is unavailable.' });
  }
});


/**
 * MCP Source Analysis API (Phase 2)
 * Direct access to the analyze_source MCP tool.
 */
app.get('/api/source/:name', async (req, res) => {
  try {
    const result = await mcpClient.callTool({
      name: 'analyze_source',
      arguments: { source: req.params.name }
    });

    if (result?.content?.[0]?.text) {
      res.json(JSON.parse(result.content[0].text));
    } else {
      res.json({ found: false, credibility: 'UNKNOWN' });
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});


/**
 * Utility Functions
 */
function extractSource(title) {
  const match = title?.match(/ - ([^-]+)$/);
  return match ? match[1].trim() : 'Google News';
}

app.listen(PORT, () => {
  console.log(`\n FactCheck Live (MCP v2.0 + ADK Bridge) running at http://localhost:${PORT}\n`);
});
