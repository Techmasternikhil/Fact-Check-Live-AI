import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

/**
 * Model Context Protocol (MCP) Server — FactCheck Live Knowledge Base
 *
 * Enhanced in Phase 2 (Day 5) to provide a richer verification surface
 * for the ADK multi-agent pipeline. Now exposes 3 tools:
 *   1. verify_fact     — headline ↔ knowledge-base matching (expanded)
 *   2. analyze_source  — source credibility tier lookup
 *   3. get_claim_context — retrieve contextual background for a claim
 */
const server = new Server(
  {
    name: 'factcheck-knowledge-base',
    version: '2.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// =========================================================================
// Expanded Knowledge Base (Phase 2)
// =========================================================================

/**
 * Each entry contains:
 *   keywords  — trigger words (match ≥2 or all if single-keyword)
 *   score     — credibility score (0-100)
 *   verdict   — classification
 *   reason    — human-readable explanation
 *   flags     — categorical tags
 *   category  — topical grouping for filtering
 *   severity  — how dangerous the misinformation is (low/medium/high/critical)
 */
const knowledgeBase = [
  // ── Medical & Health Misinformation ─────────────────────────────
  {
    keywords: ['cure', 'cancer', 'miracle'],
    score: 5,
    verdict: 'Likely Fake',
    reason: 'Medical consensus states there is no single "miracle cure" for all cancers. Such claims are unverified and potentially dangerous.',
    flags: ['Medical Misinformation', 'Unverified Claim'],
    category: 'health',
    severity: 'critical',
  },
  {
    keywords: ['vaccine', 'microchip', 'tracking'],
    score: 2,
    verdict: 'Likely Fake',
    reason: 'No injectable microchip technology exists at vaccine-needle scale. Debunked by FDA, WHO, and independent fact-checkers globally.',
    flags: ['Debunked Conspiracy', 'Health Misinformation'],
    category: 'health',
    severity: 'critical',
  },
  {
    keywords: ['5g', 'covid', 'cause'],
    score: 3,
    verdict: 'Likely Fake',
    reason: 'Debunked by WHO, CDC, and every major health authority. Radio frequency waves cannot create or transmit biological viruses.',
    flags: ['Debunked Conspiracy', 'Health Misinformation'],
    category: 'health',
    severity: 'critical',
  },
  {
    keywords: ['ivermectin', 'covid', 'cure'],
    score: 8,
    verdict: 'Likely Fake',
    reason: 'Large-scale clinical trials (TOGETHER, ACTIV-6) found no meaningful benefit of ivermectin for COVID-19 treatment.',
    flags: ['Medical Misinformation', 'Debunked Treatment'],
    category: 'health',
    severity: 'high',
  },
  {
    keywords: ['drinking', 'bleach', 'cure', 'virus'],
    score: 1,
    verdict: 'Likely Fake',
    reason: 'Ingesting bleach is extremely dangerous and can be fatal. No legitimate medical authority recommends this.',
    flags: ['Dangerous Misinformation', 'Health Hazard'],
    category: 'health',
    severity: 'critical',
  },

  // ── Conspiracy Theories ─────────────────────────────────────────
  {
    keywords: ['alien', 'ufo', 'abduction'],
    score: 10,
    verdict: 'Likely Fake',
    reason: 'No credible scientific agency has confirmed extraterrestrial abductions or visitations on Earth.',
    flags: ['Conspiracy Theory', 'Lack of Evidence'],
    category: 'conspiracy',
    severity: 'low',
  },
  {
    keywords: ['flat', 'earth', 'proof'],
    score: 5,
    verdict: 'Likely Fake',
    reason: 'Contradicts centuries of empirical evidence and satellite imagery. No credible scientific institution supports this claim.',
    flags: ['Debunked Conspiracy', 'Anti-Science'],
    category: 'conspiracy',
    severity: 'medium',
  },
  {
    keywords: ['nasa', 'moon', 'fake', 'studio'],
    score: 5,
    verdict: 'Likely Fake',
    reason: 'The Apollo moon landings are historically documented and scientifically verified with physical evidence including lunar samples.',
    flags: ['Debunked Conspiracy'],
    category: 'conspiracy',
    severity: 'medium',
  },
  {
    keywords: ['chemtrails', 'spray', 'population'],
    score: 4,
    verdict: 'Likely Fake',
    reason: 'Contrails are condensation from jet exhaust. No credible evidence supports deliberate chemical spraying from aircraft.',
    flags: ['Debunked Conspiracy', 'Pseudoscience'],
    category: 'conspiracy',
    severity: 'medium',
  },

  // ── Political Misinformation ────────────────────────────────────
  {
    keywords: ['election', 'fraud', 'stolen', 'millions'],
    score: 10,
    verdict: 'Likely Fake',
    reason: 'Claims of widespread election fraud involving millions of votes have been dismissed by over 60 courts and confirmed false by DOJ, CISA, and bipartisan officials.',
    flags: ['Debunked Claim', 'Legally Adjudicated'],
    category: 'politics',
    severity: 'high',
  },
  {
    keywords: ['deep', 'state', 'shadow', 'government'],
    score: 15,
    verdict: 'Likely Fake',
    reason: 'The "deep state" conspiracy lacks credible evidence. Government bureaucracy is not equivalent to a coordinated shadow government.',
    flags: ['Conspiracy Theory', 'Politically Charged'],
    category: 'politics',
    severity: 'medium',
  },

  // ── Climate & Environment ───────────────────────────────────────
  {
    keywords: ['climate', 'change', 'hoax'],
    score: 8,
    verdict: 'Likely Fake',
    reason: 'Overwhelming scientific consensus (IPCC, NASA, NOAA) confirms climate change is real and primarily driven by human activities.',
    flags: ['Scientific Consensus Violation', 'Misinformation'],
    category: 'climate',
    severity: 'high',
  },
  {
    keywords: ['climate', 'change', 'report', 'temperature'],
    score: 85,
    verdict: 'Likely Real',
    reason: 'Climate reporting from scientific institutions is regularly published and verifiable through peer-reviewed data.',
    flags: ['Scientifically Verified'],
    category: 'climate',
    severity: 'low',
  },

  // ── Technology (Verifiable) ─────────────────────────────────────
  {
    keywords: ['apple', 'iphone', 'release'],
    score: 85,
    verdict: 'Likely Real',
    reason: 'Tech companies like Apple regularly release new models of their flagship devices. Product announcements are easily verifiable.',
    flags: ['Standard Industry News'],
    category: 'technology',
    severity: 'low',
  },
  {
    keywords: ['google', 'ai', 'launch', 'model'],
    score: 82,
    verdict: 'Likely Real',
    reason: 'Major tech companies regularly announce AI products. Verify through official press releases and company blogs.',
    flags: ['Tech Industry News', 'Verifiable'],
    category: 'technology',
    severity: 'low',
  },
  {
    keywords: ['data', 'breach', 'million', 'hack'],
    score: 60,
    verdict: 'Uncertain',
    reason: 'Data breaches are common but specific claims require verification through official company statements or security advisories.',
    flags: ['Requires Verification', 'Cybersecurity'],
    category: 'technology',
    severity: 'medium',
  },

  // ── Economics & Finance ─────────────────────────────────────────
  {
    keywords: ['inflation', 'fed', 'interest', 'rates'],
    score: 90,
    verdict: 'Likely Real',
    reason: 'Economic news regarding inflation and Federal Reserve interest rates are standard, verifiable events published by official sources.',
    flags: ['Economic News', 'Verifiable'],
    category: 'economics',
    severity: 'low',
  },
  {
    keywords: ['stock', 'market', 'crash', 'imminent'],
    score: 30,
    verdict: 'Uncertain',
    reason: 'Market crash predictions are extremely common and rarely accurate. Exercise caution with alarmist financial predictions.',
    flags: ['Speculative', 'Financial Fearmongering'],
    category: 'economics',
    severity: 'medium',
  },
  {
    keywords: ['crypto', 'guaranteed', 'profit', 'returns'],
    score: 8,
    verdict: 'Likely Fake',
    reason: 'No investment offers guaranteed returns. Claims of guaranteed crypto profits are hallmarks of financial scams.',
    flags: ['Financial Scam', 'Fraudulent Claim'],
    category: 'economics',
    severity: 'high',
  },

  // ── Geopolitics & International ─────────────────────────────────
  {
    keywords: ['war', 'nuclear', 'imminent', 'launch'],
    score: 20,
    verdict: 'Uncertain',
    reason: 'Nuclear threat claims require verification from official defense and intelligence sources. Alarmist framing is common in misinformation.',
    flags: ['Requires Official Verification', 'Alarmist'],
    category: 'geopolitics',
    severity: 'high',
  },
  {
    keywords: ['sanctions', 'trade', 'agreement', 'bilateral'],
    score: 80,
    verdict: 'Likely Real',
    reason: 'Trade agreements and sanctions are official government actions, typically documented in public records.',
    flags: ['Government Record', 'Verifiable'],
    category: 'geopolitics',
    severity: 'low',
  },

  // ── Science & Research ──────────────────────────────────────────
  {
    keywords: ['study', 'published', 'journal', 'research'],
    score: 75,
    verdict: 'Likely Real',
    reason: 'Peer-reviewed research published in recognized journals has undergone academic scrutiny, though individual studies should be considered alongside the broader literature.',
    flags: ['Academic Source', 'Peer Reviewed'],
    category: 'science',
    severity: 'low',
  },
  {
    keywords: ['scientists', 'discover', 'cure', 'all'],
    score: 5,
    verdict: 'Likely Fake',
    reason: 'Claims of a universal cure for all diseases contradict the fundamental complexity of medicine and biology.',
    flags: ['Extraordinary Claim', 'Medical Misinformation'],
    category: 'science',
    severity: 'critical',
  },
];


// =========================================================================
// Source Credibility Registry
// =========================================================================

const sourceRegistry = {
  reputable: [
    { name: 'bbc', tier: 'Tier 1', bias: 'Center', factCheck: 'High' },
    { name: 'reuters', tier: 'Tier 1', bias: 'Center', factCheck: 'Very High' },
    { name: 'associated press', tier: 'Tier 1', bias: 'Center', factCheck: 'Very High' },
    { name: 'ap news', tier: 'Tier 1', bias: 'Center', factCheck: 'Very High' },
    { name: 'the new york times', tier: 'Tier 1', bias: 'Center-Left', factCheck: 'High' },
    { name: 'nytimes', tier: 'Tier 1', bias: 'Center-Left', factCheck: 'High' },
    { name: 'the washington post', tier: 'Tier 1', bias: 'Center-Left', factCheck: 'High' },
    { name: 'the guardian', tier: 'Tier 1', bias: 'Center-Left', factCheck: 'High' },
    { name: 'bloomberg', tier: 'Tier 1', bias: 'Center', factCheck: 'High' },
    { name: 'financial times', tier: 'Tier 1', bias: 'Center', factCheck: 'High' },
    { name: 'wsj', tier: 'Tier 1', bias: 'Center-Right', factCheck: 'High' },
    { name: 'npr', tier: 'Tier 1', bias: 'Center', factCheck: 'High' },
    { name: 'pbs', tier: 'Tier 1', bias: 'Center', factCheck: 'High' },
    { name: 'ndtv', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'the hindu', tier: 'Tier 2', bias: 'Center-Left', factCheck: 'High' },
    { name: 'times of india', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'indian express', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'hindustan times', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'mint', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'the verge', tier: 'Tier 2', bias: 'Center', factCheck: 'High' },
    { name: 'techcrunch', tier: 'Tier 2', bias: 'Center', factCheck: 'Moderate' },
    { name: 'wired', tier: 'Tier 2', bias: 'Center-Left', factCheck: 'High' },
  ],
  questionable: [
    { name: 'infowars', tier: 'Unreliable', bias: 'Far-Right', factCheck: 'Very Low' },
    { name: 'breitbart', tier: 'Unreliable', bias: 'Far-Right', factCheck: 'Low' },
    { name: 'naturalnews', tier: 'Unreliable', bias: 'Conspiracy', factCheck: 'Very Low' },
    { name: 'the gateway pundit', tier: 'Unreliable', bias: 'Far-Right', factCheck: 'Very Low' },
    { name: 'occupy democrats', tier: 'Unreliable', bias: 'Far-Left', factCheck: 'Low' },
    { name: 'palmer report', tier: 'Unreliable', bias: 'Far-Left', factCheck: 'Low' },
    { name: 'daily wire', tier: 'Mixed', bias: 'Right', factCheck: 'Mixed' },
  ],
};


// =========================================================================
// Tool Registration
// =========================================================================

server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'verify_fact',
        description: 'Verify a news headline against the expanded knowledge base. Returns a match with score, verdict, reason, flags, category, and severity if found.',
        inputSchema: {
          type: 'object',
          properties: {
            title: {
              type: 'string',
              description: 'The news headline to verify',
            },
            source: {
              type: 'string',
              description: 'The source of the news (optional)',
            },
          },
          required: ['title'],
        },
      },
      {
        name: 'analyze_source',
        description: 'Look up a news source in the credibility registry. Returns tier, bias rating, and fact-check reliability score.',
        inputSchema: {
          type: 'object',
          properties: {
            source: {
              type: 'string',
              description: 'The name of the news source to evaluate',
            },
          },
          required: ['source'],
        },
      },
      {
        name: 'get_claim_context',
        description: 'Retrieve contextual background for a factual claim. Searches the knowledge base by category and returns related entries for broader context.',
        inputSchema: {
          type: 'object',
          properties: {
            claim: {
              type: 'string',
              description: 'The factual claim to get context for',
            },
            category: {
              type: 'string',
              description: 'Optional category filter (health, conspiracy, politics, climate, technology, economics, geopolitics, science)',
            },
          },
          required: ['claim'],
        },
      },
    ],
  };
});


// =========================================================================
// Tool Handlers
// =========================================================================

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const toolName = request.params.name;

  // ── Tool 1: verify_fact (enhanced) ──────────────────────────────
  if (toolName === 'verify_fact') {
    const title = (request.params.arguments?.title || '').toLowerCase();
    const source = (request.params.arguments?.source || '').toLowerCase();

    // Weighted matching: score each KB entry
    let bestMatch = null;
    let bestScore = 0;

    for (const entry of knowledgeBase) {
      const matchCount = entry.keywords.filter(kw => title.includes(kw)).length;
      const matchRatio = matchCount / entry.keywords.length;

      // Require at least 2 keyword matches, or all keywords for single-keyword entries
      if (
        (entry.keywords.length > 1 && matchCount >= 2) ||
        (entry.keywords.length === 1 && matchCount === 1)
      ) {
        // Weight by match ratio — better matches get priority
        const weightedScore = matchRatio * 100 + matchCount * 10;
        if (weightedScore > bestScore) {
          bestScore = weightedScore;
          bestMatch = entry;
        }
      }
    }

    if (bestMatch) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            matchFound: true,
            score: bestMatch.score,
            verdict: bestMatch.verdict,
            reason: bestMatch.reason,
            flags: bestMatch.flags,
            category: bestMatch.category,
            severity: bestMatch.severity,
            confidence: Math.min(bestScore, 100),
          }),
        }],
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({ matchFound: false }),
      }],
    };
  }

  // ── Tool 2: analyze_source ──────────────────────────────────────
  if (toolName === 'analyze_source') {
    const source = (request.params.arguments?.source || '').toLowerCase();

    // Search reputable sources
    const reputable = sourceRegistry.reputable.find(s =>
      source.includes(s.name)
    );
    if (reputable) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            found: true,
            name: reputable.name,
            credibility: 'REPUTABLE',
            tier: reputable.tier,
            bias: reputable.bias,
            factCheckReliability: reputable.factCheck,
            scoreImpact: reputable.tier === 'Tier 1' ? +30 : +20,
            recommendation: `${reputable.name} is a ${reputable.tier} source with ${reputable.factCheck} fact-check reliability. Generally trustworthy.`,
          }),
        }],
      };
    }

    // Search questionable sources
    const questionable = sourceRegistry.questionable.find(s =>
      source.includes(s.name)
    );
    if (questionable) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            found: true,
            name: questionable.name,
            credibility: 'QUESTIONABLE',
            tier: questionable.tier,
            bias: questionable.bias,
            factCheckReliability: questionable.factCheck,
            scoreImpact: -30,
            recommendation: `${questionable.name} is rated ${questionable.tier} with ${questionable.bias} bias. Exercise extreme caution.`,
          }),
        }],
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          found: false,
          credibility: 'UNKNOWN',
          scoreImpact: -5,
          recommendation: 'Source not found in registry. Cannot confirm editorial standards. Recommend cross-referencing with known outlets.',
        }),
      }],
    };
  }

  // ── Tool 3: get_claim_context ───────────────────────────────────
  if (toolName === 'get_claim_context') {
    const claim = (request.params.arguments?.claim || '').toLowerCase();
    const category = (request.params.arguments?.category || '').toLowerCase();

    // Find all entries that partially match the claim
    let matches = knowledgeBase.filter(entry => {
      const keywordMatch = entry.keywords.some(kw => claim.includes(kw));
      if (category) {
        return keywordMatch && entry.category === category;
      }
      return keywordMatch;
    });

    if (matches.length === 0 && category) {
      // If no keyword match in category, return all entries in that category
      matches = knowledgeBase.filter(entry => entry.category === category);
    }

    if (matches.length > 0) {
      return {
        content: [{
          type: 'text',
          text: JSON.stringify({
            contextFound: true,
            totalRelated: matches.length,
            entries: matches.slice(0, 5).map(m => ({
              keywords: m.keywords,
              verdict: m.verdict,
              score: m.score,
              reason: m.reason,
              category: m.category,
              severity: m.severity,
            })),
            summary: `Found ${matches.length} related knowledge base entries. ${matches.filter(m => m.verdict === 'Likely Fake').length} flagged as misinformation.`,
          }),
        }],
      };
    }

    return {
      content: [{
        type: 'text',
        text: JSON.stringify({
          contextFound: false,
          summary: 'No related context found in knowledge base. Claim is novel or outside current coverage.',
        }),
      }],
    };
  }

  throw new Error(`Unknown tool: ${toolName}`);
});


// =========================================================================
// Server Initialization
// =========================================================================

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('FactCheck Knowledge Base MCP Server v2.0 running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
