"""
MarketTrust AI — LLM Prompt Templates.

All prompts used for claim extraction, verification, and analysis
are centralized here for maintainability.
"""

# ── Claim Extraction Prompt ─────────────────────────────────

CLAIM_EXTRACTION_PROMPT = """\
You are a financial claim extractor specializing in Indian financial markets. \
Given the following text from a financial communication, extract ALL verifiable \
factual claims as structured triples.

Focus on:
- Financial performance claims (returns, profits, growth)
- Regulatory claims (SEBI registered, licensed, authorized)
- Identity claims (company name, broker name, credentials)
- Prediction claims (stock tips, market forecasts, guaranteed returns)
- Urgency claims (limited time offers, exclusive access)
- Risk claims (risk-free, guaranteed, no-loss)

For each claim, assess your confidence in the extraction accuracy (0.0 to 1.0).
Also categorize each claim: "financial", "regulatory", "performance", "identity", \
"prediction", or "urgency".

Output ONLY a valid JSON array. No markdown, no explanation.

Format:
[
  {{
    "subject": "entity or person making the claim",
    "predicate": "what is being claimed (verb/relationship)",
    "object": "the specific claim content",
    "confidence": 0.85,
    "raw_text": "original text this claim was extracted from",
    "category": "financial"
  }}
]

If no verifiable claims are found, return an empty array: []

Text to analyze:
{text}
"""

# ── Evidence Verification Prompt ────────────────────────────

EVIDENCE_VERIFICATION_PROMPT = """\
You are a financial claim verifier specializing in Indian financial markets.

Given the following claim, assess whether it is likely TRUE or FALSE based on \
your knowledge. Provide your reasoning.

Claim:
- Subject: {subject}
- Predicate: {predicate}
- Object: {object}

Consider:
1. Is this claim factually verifiable?
2. Does it match known facts about Indian financial markets?
3. Are there any red flags (unrealistic returns, unregistered entities, etc.)?
4. What is the confidence in your assessment?

Output ONLY a valid JSON object:
{{
  "supports": true or false,
  "confidence": 0.0 to 1.0,
  "explanation": "Your reasoning here",
  "red_flags": ["list of any red flags found"]
}}
"""

# ── Trust Assessment Prompt ─────────────────────────────────

TRUST_ASSESSMENT_PROMPT = """\
You are a financial trust assessor. Given the following information about a \
financial communication, provide an overall trust assessment.

Communication Type: {media_type}
Number of Claims: {claims_count}
Verified Claims: {verified_count}
Contradicted Claims: {contradicted_count}

Claims Summary:
{claims_summary}

Evidence Summary:
{evidence_summary}

Provide a recommendation in the following JSON format:
{{
  "recommendation": "Your recommendation text (2-3 sentences)",
  "key_concerns": ["list of key concerns"],
  "positive_signals": ["list of positive signals"],
  "risk_factors": ["specific risk factors identified"]
}}
"""

# ── Red Flag Detection Prompt ───────────────────────────────

RED_FLAG_PROMPT = """\
Analyze the following text for common financial fraud red flags in the Indian \
market context:

Text: {text}

Red flags to look for:
- Guaranteed returns or "no-loss" promises
- Pressure tactics (limited time, act now)
- Unverifiable credentials or fake SEBI registration
- Unrealistic return percentages (>30% per month)
- Requests for money via informal channels (UPI, direct transfer)
- Claims of insider information
- Missing risk disclaimers
- Impersonation of known entities

Output ONLY a valid JSON array of detected red flags:
[
  {{
    "flag": "Description of the red flag",
    "severity": "high" or "medium" or "low",
    "evidence": "The text that triggered this flag"
  }}
]

If no red flags found, return: []
"""
