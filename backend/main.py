"""
AI Reality Integrity Engine - Standalone Backend (Grok)

- Extracts factual claims from user text
- Retrieves web evidence (optional: Tavily)
- Runs NLI-style verification with Grok model
- Aggregates into a final truth score and verdict

Run with:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import os
import uuid
import json
import datetime as dt
from typing import List, Dict, Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, constr

# ---------------------------------------------------------------------
# Environment & clients
# ---------------------------------------------------------------------
load_dotenv()

# GROK configuration (set these in your environment or .env)
# Accept either `GROK_API_KEY` or `GROQ_API_KEY` (some .env files use the latter)
GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
# Default endpoint — Groq provides OpenAI-compatible endpoints. Use the chat completions
# endpoint by default, or override with `GROK_API_URL` / `GROQ_API_URL` in your environment.
# Common Groq endpoints:
#  - Chat completions (OpenAI-compatible): https://api.groq.com/openai/v1/chat/completions
#  - Responses API:                          https://api.groq.com/openai/v1/responses
GROK_API_URL = os.getenv(
    "GROK_API_URL",
    os.getenv(
        "GROQ_API_URL",
        "https://api.groq.com/openai/v1/chat/completions",
    ),
)

# If you still have an OpenAI key but want to use Grok, you can ignore OPENAI_API_KEY
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # kept for backward compatibility (not used)
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # optional
TAVILY_URL = "https://api.tavily.com/v1/search"


# Basic check so user gets a helpful error early
if not GROK_API_KEY:
    # Do not outright raise here so the server can start in some dev cases (e.g., you only want to test extraction).
    # But many endpoints will fail without a key — raise when we attempt to call Grok.
    pass

# ---------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------

class VerifyRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10_000, description="User text / document to verify")
    user_id: Optional[str] = Field(None, description="Optional user id")
    language: Optional[str] = Field("en", description="Output language (for explanations)")

class Claim(BaseModel):
    claim_id: str
    text: str
    claim_type: str
    tokens: int
    extracted_entities: List[str] = []
    char_span: List[int] = []

class EvidenceSnippet(BaseModel):
    source: str
    url: Optional[str] = None
    title: Optional[str] = None
    snippet: str

class ClaimVerification(BaseModel):
    claim_id: str
    label: str  # SUPPORT | CONTRADICT | NEUTRAL
    entailment_score: float
    extracted_facts: Dict[str, Any]
    explanation: str
    evidence_used: List[EvidenceSnippet]

class ClaimVerdict(BaseModel):
    claim_id: str
    claim_text: str
    label: str
    score: float
    confidence: float
    verdict: str
    rationale: str
    evidence_used: List[EvidenceSnippet]

class VerifyResponse(BaseModel):
    job_id: str
    run_id: str
    created_at: str
    original_text: str
    claims: List[Claim]
    verifications: List[ClaimVerdict]
    overall_summary: str

# ---------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------
app = FastAPI(
    title="AI Reality Integrity Engine",
    version="0.2.0",
    description="Standalone fact-checking backend using Grok",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# Grok helpers
# ---------------------------------------------------------------------
async def _call_grok_api(system_prompt: str, user_prompt: str, model: Optional[str] = None, temperature: float = 0.1) -> str:
    """
    Generic async POST to a Grok-like chat endpoint.

    This function is intentionally tolerant to different response shapes:
    - It will try to parse JSON responses that include 'choices', 'output', 'text', or 'content'.
    - If the API returns plain text, it will return the response body.
    - If Grok requires a different payload/param names, adjust GROK_PAYLOAD below.
    """
    if not GROK_API_KEY:
        raise HTTPException(status_code=500, detail="GROK_API_KEY not configured in environment")

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    # Generic payload — adapt to your Grok provider's expected schema if needed
    grok_payload = {
        "model": model or "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }


    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(GROK_API_URL, json=grok_payload, headers=headers)
            resp.raise_for_status()
            # Try JSON first
            try:
                resp_json = resp.json()
            except Exception:
                # Not JSON — return raw text
                return resp.text

            # Extract textual output from common fields
            # 1) OpenAI-like: choices[0].message.content or choices[0].text
            if isinstance(resp_json, dict):
                choices = resp_json.get("choices")
                if choices and isinstance(choices, list) and len(choices) > 0:
                    first = choices[0]
                    # message.content
                    if isinstance(first, dict):
                        msg = first.get("message") or first.get("delta") or first
                        if isinstance(msg, dict) and "content" in msg:
                            return msg["content"]
                        if "text" in first:
                            return first["text"]
                # 2) other providers: top-level 'output' or 'text' or 'content'
                for key in ("output", "text", "content", "result"):
                    if key in resp_json and isinstance(resp_json[key], str):
                        return resp_json[key]
                # 3) sometimes output is nested
                if "response" in resp_json and isinstance(resp_json["response"], str):
                    return resp_json["response"]

            # Fallback to stringified JSON
            return json.dumps(resp_json)
    except httpx.HTTPStatusError as he:
        raise HTTPException(status_code=502, detail=f"Grok API returned error: {he.response.status_code} {he.response.text}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Error calling Grok API: {e}")

async def _chat_json(system_prompt: str, user_prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Use Grok (or other configured chat endpoint) to produce a JSON object.
    We instruct the model to return machine-readable JSON; then parse it.
    """
    # ask the model to output JSON only
    # You may want to tailor this 'instruction' to match Grok's best practices
    json_instruction = (
        "IMPORTANT: Return ONLY valid JSON (no explanatory text) as the assistant response. "
        "The JSON must be parseable by a JSON parser."
    )
    system = system_prompt + "\n\n" + json_instruction

    raw_text = await _call_grok_api(
    system,
    user_prompt,
    model=model or "llama-3.3-70b-versatile",
    temperature=0.1
)


    # The model may return JSON directly, or return text that contains JSON. Try to extract JSON.
    # First attempt: parse raw_text as JSON directly.
    try:
        return json.loads(raw_text)
    except Exception:
        # Try to find a JSON substring inside the text (first { ... } block)
        try:
            start = raw_text.index("{")
            end = raw_text.rindex("}") + 1
            possible = raw_text[start:end]
            return json.loads(possible)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse JSON from Grok response: {e}; raw={raw_text!r}",
            )

# ---------------------------------------------------------------------
# Step 1 – Claim extraction
# ---------------------------------------------------------------------
async def extract_claims(text: str, language: str = "en") -> List[Claim]:
    system_prompt = (
        "You are a precise factual claim extraction engine. "
        "Extract all discrete factual statements suitable for fact-checking. "
        "Return only machine-readable JSON."
    )
    user_prompt = f"""
Input text:
\"\"\"{text}\"\"\".

Return a JSON object with a single key "claims", where "claims" is a list of objects:
{{
  "claim_id": "c1",
  "text": "<exact claim text>",
  "claim_type": "numerical | comparative | categorical | temporal | causal",
  "tokens": <approximate token count>,
  "extracted_entities": ["entities, names, dates, quantities"],
  "char_span": [start_index, end_index]
}}

If there are no factual claims, return "claims": [].
Use language: {language}.
"""

    data = await _chat_json(system_prompt, user_prompt)
    raw_claims = data.get("claims", [])

    claims: List[Claim] = []
    for i, c in enumerate(raw_claims, start=1):
        try:
            claims.append(
                Claim(
                    claim_id=c.get("claim_id") or f"c{i}",
                    text=c["text"],
                    claim_type=c.get("claim_type", "categorical"),
                    tokens=int(c.get("tokens", 10)),
                    extracted_entities=c.get("extracted_entities", []) or [],
                    char_span=c.get("char_span", [0, 0]) or [0, 0],
                )
            )
        except Exception:
            # Skip malformed entries instead of failing hard
            continue
    return claims
# ---------------------------------------------------------------------
# Step 2 – Web retrieval (Correct Tavily API 2025)
# ---------------------------------------------------------------------
async def retrieve_evidence_for_claim(claim: Claim, max_results: int = 5):
    import httpx

    url = "https://api.duckduckgo.com/"
    params = {
        "q": claim.text,
        "format": "json",
        "no_html": 1,
        "no_redirect": 1
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        print("DDG ERROR:", e)
        return []

    snippets = []

    # Main abstract
    if data.get("Abstract"):
        snippets.append(
            EvidenceSnippet(
                source="web:ddg",
                title=data.get("Heading"),
                url=data.get("AbstractURL"),
                snippet=data.get("Abstract")
            )
        )

    # Related topic snippets
    for topic in data.get("RelatedTopics", [])[:3]:
        if isinstance(topic, dict) and topic.get("Text"):
            snippets.append(
                EvidenceSnippet(
                    source="web:ddg",
                    title=topic.get("FirstURL"),
                    url=topic.get("FirstURL"),
                    snippet=topic.get("Text")
                )
            )

    return snippets



# ---------------------------------------------------------------------
# Step 3 – Claim verification (NLI)
# ---------------------------------------------------------------------
async def verify_claim_with_evidence(
    claim: Claim,
    evidence: List[EvidenceSnippet],
    language: str = "en",
) -> ClaimVerification:
    evidence_texts = [
        f"[{i+1}] {e.title or ''} {e.snippet} (source: {e.url or e.source})"
        for i, e in enumerate(evidence)
    ]

    joined_evidence = "\n\n".join(evidence_texts) if evidence_texts else "NO_EVIDENCE_AVAILABLE"

    system_prompt = (
        "You are a rigorous fact-checking engine using Natural Language Inference (NLI). "
        "Given a claim and a collection of evidence snippets, decide whether the evidence "
        "SUPPORTS, CONTRADICTS, or is NEUTRAL with respect to the claim. "
        "Be conservative: if evidence is incomplete or ambiguous, respond NEUTRAL."
    )

    user_prompt = f"""
Claim:
\"\"\"{claim.text}\"\"\".

Evidence snippets:
\"\"\"{joined_evidence}\"\"\".

Return a JSON object:
{{
  "label": "SUPPORT" | "CONTRADICT" | "NEUTRAL",
  "entailment_score": <float between 0 and 1>,
  "extracted_facts": {{
      "numbers": [...],
      "dates": [...],
      "entities": [...],
      "extra": "..."
  }},
  "explanation": "Short explanation in {language}."
}}
"""

    data = await _chat_json(system_prompt, user_prompt)

    label = str(data.get("label", "NEUTRAL")).upper()
    if label not in {"SUPPORT", "CONTRADICT", "NEUTRAL"}:
        label = "NEUTRAL"

    try:
        score = float(data.get("entailment_score", 0.0))
    except Exception:
        score = 0.0

    extracted_facts = data.get("extracted_facts", {}) or {}
    explanation = data.get("explanation", "")

    return ClaimVerification(
        claim_id=claim.claim_id,
        label=label,
        entailment_score=max(0.0, min(1.0, score)),
        extracted_facts=extracted_facts,
        explanation=explanation,
        evidence_used=evidence,
    )

# ---------------------------------------------------------------------
# Step 4 – Truth scoring & verdicts
# ---------------------------------------------------------------------
def aggregate_verdict(claim: Claim, verification: ClaimVerification) -> ClaimVerdict:
    # Map NLI output to final truth score (0–1) & verdict label
    S = verification.entailment_score if verification.label == "SUPPORT" else 0.0
    C = verification.entailment_score if verification.label == "CONTRADICT" else 0.0

    # Simple scoring formula similar to the earlier design
    truth_score = max(0.0, min(1.0, S - C))
    confidence = max(0.1, S)  # minimum confidence

    if S >= 0.70 and C < 0.30:
        verdict = "VERIFIED"
    elif S >= 0.35 and C >= 0.30:
        verdict = "PARTIALLY_SUPPORTED"
    elif S == 0 and C == 0:
        verdict = "UNVERIFIED"
    else:
        verdict = "UNVERIFIED"

    rationale = verification.explanation

    return ClaimVerdict(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        label=verification.label,
        score=truth_score,
        confidence=confidence,
        verdict=verdict,
        rationale=rationale,
        evidence_used=verification.evidence_used,
    )

# ---------------------------------------------------------------------
# Step 5 – Summary
# ---------------------------------------------------------------------
async def summarize_overall(verdicts: List[ClaimVerdict], language: str = "en") -> str:
    system_prompt = (
        "You are an AI analyst summarising a fact-checking run for a human reader. "
        "You receive a list of claim verdicts. Produce a short, clear overview."
    )

    bullets = []
    for v in verdicts:
        bullets.append(
            f"- Claim: {v.claim_text}\n"
            f"  Verdict: {v.verdict} (score={v.score:.2f}, confidence={v.confidence:.2f})\n"
            f"  Explanation: {v.rationale}"
        )
    user_prompt = f"""
Language: {language}

Claim verdicts:
{chr(10).join(bullets)}

Write a short executive summary (2–4 sentences).
"""

    data = await _chat_json(system_prompt, user_prompt)
    # Allow either {"summary": "..."} or {"text": "..."} or anything with "summary"
    summary = (
        data.get("summary")
        or data.get("text")
        or data.get("overall")
        or json.dumps(data)
    )
    return summary

# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "message": "AI Reality Integrity Engine backend running"}


@app.get("/", response_class=HTMLResponse)
async def root():
        """Small landing page to avoid 404s on root requests.

        Link to OpenAPI docs is provided for convenience.
        """
        html = """
        <html>
            <head>
                <title>AI Reality Integrity Engine</title>
            </head>
            <body>
                <h1>AI Reality Integrity Engine</h1>
                <p>Backend running. Use the <a href="/docs">API docs</a> or the <a href="/health">health</a> endpoint.</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html, status_code=200)


@app.get("/favicon.ico")
async def favicon():
        # Return no content to avoid 404 noise from browsers
        return Response(status_code=204)

@app.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    """
    End-to-end verification pipeline:
      1. Extract factual claims from input text
      2. Retrieve web evidence for each claim (if Tavily available)
      3. Run NLI verification with Grok
      4. Aggregate truth scores & build final summary
    """
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    created_at = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    # 1. Claim extraction
    claims = await extract_claims(req.text, language=req.language)
    if not claims:
        # still return a valid response
        return VerifyResponse(
            job_id=job_id,
            run_id=run_id,
            created_at=created_at,
            original_text=req.text,
            claims=[],
            verifications=[],
            overall_summary="No factual claims were detected in the input.",
        )

    verifications: List[ClaimVerdict] = []

    # 2–4 for each claim
    for claim in claims:
        evidence = await retrieve_evidence_for_claim(claim)
        verification = await verify_claim_with_evidence(
            claim, evidence, language=req.language
        )
        verdict = aggregate_verdict(claim, verification)
        verifications.append(verdict)

    # 5. Overall summary
    overall = await summarize_overall(verifications, language=req.language)

    return VerifyResponse(
        job_id=job_id,
        run_id=run_id,
        created_at=created_at,
        original_text=req.text,
        claims=claims,
        verifications=verifications,
        overall_summary=overall,
    )
