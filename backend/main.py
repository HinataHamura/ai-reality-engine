"""
AI Reality Integrity Engine - Standalone Backend (Grok)

- Extracts factual claims from user text
- Retrieves web evidence (DuckDuckGo fallback)
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
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------
load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
GROK_API_URL = os.getenv(
    "GROK_API_URL",
    os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions"),
)

if not GROK_API_KEY:
    print("WARNING: GROK_API_KEY missing — backend will fail for verification requests")

# ---------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------
class VerifyRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    language: Optional[str] = "en"

class Claim(BaseModel):
    claim_id: str
    text: str
    claim_type: str
    tokens: int
    extracted_entities: List[str]
    char_span: List[int]

class EvidenceSnippet(BaseModel):
    source: str
    url: Optional[str]
    title: Optional[str]
    snippet: str

class ClaimVerification(BaseModel):
    claim_id: str
    label: str
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
    version="1.0.0",
    description="Standalone fact-checking backend using Grok + DuckDuckGo Evidence",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# GROK caller
# ---------------------------------------------------------------------
async def _call_grok_api(system_prompt: str, user_prompt: str) -> str:

    if not GROK_API_KEY:
        raise HTTPException(status_code=500, detail="GROK_API_KEY missing")

    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(GROK_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Grok API error: {e}")

async def _chat_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    full_system = system_prompt + "\nIMPORTANT: Return ONLY pure JSON."
    raw = await _call_grok_api(full_system, user_prompt)

    try:
        return json.loads(raw)
    except:
        try:
            start, end = raw.index("{"), raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except:
            raise HTTPException(status_code=500, detail=f"JSON parse error: {raw}")

# ---------------------------------------------------------------------
# Step 1 — Claim Extraction
# ---------------------------------------------------------------------
async def extract_claims(text: str, language: str = "en") -> List[Claim]:

    system = "Extract factual statements. Return JSON only."
    user = f"""
Text:
\"\"\"{text}\"\"\"

Return:
{{
 "claims":[
   {{
     "claim_id":"c1",
     "text":"..",
     "claim_type":"categorical",
     "tokens":5,
     "extracted_entities":["A","B"],
     "char_span":[0,20]
   }}
 ]
}}
"""

    data = await _chat_json(system, user)
    claims = []
    for i, c in enumerate(data.get("claims", []), start=1):
        claims.append(
            Claim(
                claim_id=c.get("claim_id", f"c{i}"),
                text=c["text"],
                claim_type=c.get("claim_type", "categorical"),
                tokens=int(c.get("tokens", 5)),
                extracted_entities=c.get("extracted_entities", []),
                char_span=c.get("char_span", [0, 0]),
            )
        )
    return claims

# ---------------------------------------------------------------------
# Step 2 — Evidence (DuckDuckGo Search)
# ---------------------------------------------------------------------
async def retrieve_evidence_for_claim(claim: Claim, max_results: int = 5):

    url = "https://api.duckduckgo.com/"
    params = {"q": claim.text, "format": "json", "no_redirect": 1, "no_html": 1}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            data = r.json()
    except:
        return []

    snippets = []
    if data.get("Abstract"):
        snippets.append(
            EvidenceSnippet(
                source="web:ddg",
                title=data.get("Heading"),
                url=data.get("AbstractURL"),
                snippet=data.get("Abstract"),
            )
        )

    for t in data.get("RelatedTopics", [])[:3]:
        if isinstance(t, dict) and t.get("Text"):
            snippets.append(
                EvidenceSnippet(
                    source="web:ddg",
                    title=t.get("FirstURL"),
                    url=t.get("FirstURL"),
                    snippet=t.get("Text"),
                )
            )

    return snippets

# ---------------------------------------------------------------------
# Step 3 — Verification (NLI)
# ---------------------------------------------------------------------
async def verify_claim_with_evidence(claim: Claim, evidence: List[EvidenceSnippet], language: str):

    if evidence:
        joined = "\n\n".join(
            f"[{i+1}] {e.title}: {e.snippet}" for i, e in enumerate(evidence)
        )
    else:
        joined = (
            "No external evidence. Use general world knowledge, science, history, and "
            "geographical facts to evaluate the claim."
        )

    system = "You are a fact-checking NLI system. Return JSON only."
    user = f"""
Claim: \"{claim.text}\"

Evidence:
\"\"\"{joined}\"\"\"

Return:
{{
 "label":"SUPPORT"|"CONTRADICT"|"NEUTRAL",
 "entailment_score":0.0,
 "extracted_facts":{{}},
 "explanation":"..."
}}
"""

    data = await _chat_json(system, user)

    label = data.get("label", "NEUTRAL").upper()
    if label not in {"SUPPORT", "CONTRADICT", "NEUTRAL"}:
        label = "NEUTRAL"

    score = float(data.get("entailment_score", 0.0))
    explanation = data.get("explanation", "")

    return ClaimVerification(
        claim_id=claim.claim_id,
        label=label,
        entailment_score=score,
        extracted_facts=data.get("extracted_facts", {}),
        explanation=explanation,
        evidence_used=evidence,
    )

# ---------------------------------------------------------------------
# Step 4 — Verdict aggregation
# ---------------------------------------------------------------------
def aggregate_verdict(claim: Claim, v: ClaimVerification) -> ClaimVerdict:

    S = v.entailment_score if v.label == "SUPPORT" else 0.0
    C = v.entailment_score if v.label == "CONTRADICT" else 0.0

    truth_score = max(0.0, min(1.0, S - C))

    if v.label == "SUPPORT":
        confidence = max(0.8, S)
        verdict = "TRUE"
    elif v.label == "CONTRADICT":
        confidence = max(0.8, C)
        verdict = "FALSE"
    else:
        confidence = 0.10
        verdict = "UNVERIFIED"

    return ClaimVerdict(
        claim_id=claim.claim_id,
        claim_text=claim.text,
        label=v.label,
        score=truth_score,
        confidence=confidence,
        verdict=verdict,
        rationale=v.explanation,
        evidence_used=v.evidence_used,
    )

# ---------------------------------------------------------------------
# Step 5 — Summary
# ---------------------------------------------------------------------
async def summarize_overall(verdicts: List[ClaimVerdict], language: str):

    system = "Summarize fact-checking results. JSON only."
    bullets = "\n".join(
        f"- {v.claim_text}: {v.verdict} ({v.confidence:.2f})"
        for v in verdicts
    )

    user = f"""
Language: {language}

Verdicts:
{bullets}

Return: {{"summary":"..."}}
"""

    data = await _chat_json(system, user)
    return data.get("summary", json.dumps(data))

# ---------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "message": "AI Reality Integrity Engine backend running"}

@app.get("/")
async def root():
    return HTMLResponse(
        "<h1>AI Reality Integrity Engine</h1><p>Backend running.</p>"
    )

@app.post("/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):

    job_id = f"job-{uuid.uuid4().hex[:12]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    created_at = dt.datetime.utcnow().isoformat() + "Z"

    claims = await extract_claims(req.text, req.language)
    verifications = []

    for c in claims:
        evidence = await retrieve_evidence_for_claim(c)
        vc = await verify_claim_with_evidence(c, evidence, req.language)
        verdict = aggregate_verdict(c, vc)
        verifications.append(verdict)

    summary = await summarize_overall(verifications, req.language)

    return VerifyResponse(
        job_id=job_id,
        run_id=run_id,
        created_at=created_at,
        original_text=req.text,
        claims=claims,
        verifications=verifications,
        overall_summary=summary,
    )
