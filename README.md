# AI Reality Integrity Engine

AI Reality Integrity Engine is a full‑stack, end‑to‑end fact verification platform that extracts factual claims from user text, retrieves evidence, performs NLI‑based reasoning, and produces a final verdict plus confidence scoring.
## Opus Workflow

Automated pipeline configuration:
https://app.opus.com/app/workflow/share/074d27e4-929d-41b7-bc3f-a589621be865
## Demo Videos

- AI Reality Engine (main demo) — included in the repository as `AI Reality Engine.mp4`
- Frontend walkthrough — included as `video-*.mp4`
## Overview

This project implements an automated pipeline for claim extraction, evidence retrieval, and claim verification using modern LLMs and free evidence sources. It provides both a FastAPI backend (serving the verification engine) and a Streamlit frontend (interactive UI for users).

Key capabilities:
- Automatic claim extraction from natural text (Grok LLM)
- Evidence retrieval with DuckDuckGo (primary) and automatic fallback
- NLI-based verification (SUPPORT / CONTRADICT / NEUTRAL) using Grok (llama-3.3-70b series)
- Final truth scoring and confidence metrics
- Streamlit frontend for inspection and visualization
- Opus workflow to automate the pipeline

Demo videos are included in the repository:
- Main demo video
- Frontend walkthrough video

## Features

- Claim Extraction: Extract factual statements from user‑submitted text using Grok LLM.
- Evidence Retrieval: Retrieve structured evidence snippets primarily via DuckDuckGo. Automatic fallback when Tavily is unavailable.
- NLI Verification: Run Natural Language Inference using Grok (Llama 3.3 70B) to produce SUPPORT, CONTRADICT or NEUTRAL for each claim along with reasoning.
- Truth & Confidence Scoring: Verdicts mapped to TRUE / FALSE / PARTIALLY SUPPORTED / UNVERIFIED plus a 0–1 truth score and a confidence score.
- Streamlit Frontend: Real‑time verification interface with JSON inspector, claim list, and visualization.
- Automation: Opus workflow automates the end‑to‑end pipeline.

## Tech Stack

- Frontend: Streamlit (Python)
- Backend: FastAPI (Python)
- Evidence Search: DuckDuckGo (free fallback)
- LLM Reasoning: Grok (llama-3.3-70b‑versatile)
- Orchestration: Opus workflow
- Hosting examples: Render, GitHub Codespaces

## Project Structure

ai-reality-engine/
│
├── backend/
│   ├── main.py            # FastAPI fact-checking API
│   ├── requirements.txt
│
├── frontend/
│   ├── app.py             # Streamlit UI
│
├── render.yaml            # Render deployment config
├── README.md              # (this file)
├── AI Reality Engine.mp4  # Demo video
└── video-*.mp4            # Frontend video

## Quickstart

Clone the repository:

```bash
git clone https://github.com/HinataHamura/ai-reality-engine.git
cd ai-reality-engine
```

### Backend (FastAPI)

1. Create and activate a Python virtual environment:
   - Linux / macOS:
     ```bash
     cd backend
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     cd backend
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (create `.env` inside `/backend`):
   ```
   GROK_API_KEY=your_grok_api_key
   ```

4. Run the backend:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

Backend will be available at:
http://localhost:8000

### Frontend (Streamlit)

1. Install frontend dependencies:
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. Configure backend URL used by the frontend (e.g., in frontend configuration or environment):
   ```
   BACKEND_URL=http://localhost:8000
   ```

3. Run Streamlit:
   ```bash
   streamlit run app.py
   ```

Open the Streamlit UI in your browser (usually http://localhost:8501).

## Deployment

A sample `render.yaml` is included to configure deployment on Render. When deploying, update the frontend's BACKEND_URL to your deployed backend URL, for example:

```
https://your-backend.onrender.com
```

## How it Works (Pipeline)

USER TEXT
   ↓
1) Claim Extraction (LLM)
   ↓
2) Evidence Retrieval (DuckDuckGo)
   ↓
3) NLI Verification (SUPPORT / CONTRADICT / NEUTRAL)
   ↓
4) Truth Score Computation
   ↓
5) Summary Generation
   ↓
RESULT DISPLAYED IN FRONTEND

## Example Input / Output

Example input:
- "Coffee improves life expectancy."
- "Pluto is a planet."
- "The Mediterranean diet cures cancer."

Example output table:

| Claim                                  | Result                    | Confidence |
|----------------------------------------|---------------------------|------------|
| Coffee improves life expectancy        | ✅ TRUE                   | 0.80       |
| Pluto is a planet                      | ❌ FALSE                  | 0.80       |
| Mediterranean diet cures cancer        | ❌ FALSE                  | 0.80       |

(These are example outputs; real outputs depend on the evidence retrieved and the model reasoning.)

## Roadmap

Planned enhancements:
- Add Wikipedia API as an evidence source
- Add multilingual fact‑checking
- Add RAG (Retrieval-Augmented Generation) based evidence evaluation
- Add timeline verification for historical claims
- Add image-based claim extraction
- Improve UI/UX and add more visualization components

## Contributing

Contributions are welcome! Please open issues or submit pull requests. Suggested workflow:
1. Fork the repository
2. Create a feature branch
3. Make your changes and add tests/documentation where applicable
4. Submit a pull request describing your changes

## License

This project is released under the MIT License.

## Contact / Maintainer

Maintainer: Most.Atkia Farzana  
GitHub: https://github.com/HinataHamura


---

If you'd like, I can:
- Produce a shorter README variant (one‑page quickstart)
- Add badges (build, license, coverage)
- Create example API docs and sample requests for the FastAPI backend
Tell me which you'd prefer and I’ll update the README accordingly.
