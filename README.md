🚨 AI Reality Integrity Engine
A Full-Stack AI System for Automated Fact-Checking, Truth Scoring & Claim Verification
AI Reality Integrity Engine is an end-to-end fact-verification platform that extracts factual claims from user text, retrieves evidence, performs NLI-based reasoning, and generates a final verdict with confidence scoring.

📌 Opus Workflow:
https://workflow.opus.com/workflow/t15sqBnG4y9fN4np

The project includes:
✅ FastAPI backend (Grok-powered NLI engine)
✅ Streamlit frontend (clean UI for verifying text)
✅ Opus workflow (automated pipeline logic)
✅ Demo video & frontend walk-through
✅ DuckDuckGo fallback evidence system (Tavily-free)

🎥 Demo Videos

🔹 Main Demo Video: (included in repository)
🔹 Frontend Walkthrough: (included in repository)

📌 Opus Workflow:
https://workflow.opus.com/workflow/t15sqBnG4y9fN4np

📌 Repository:
https://github.com/HinataHamura/ai-reality-engine

🚀 Key Features
🧩 1. Claim Extraction

Extracts factual statements automatically using Grok LLM.

🔍 2. Evidence Retrieval

Primary: DuckDuckGo Search

Automatic fallback when Tavily is unavailable

Cleanly structured evidence snippets

🧠 3. NLI-powered Claim Verification

Using Grok’s Llama-3 series model:

SUPPORT

CONTRADICT

NEUTRAL

With reasoning + explanation.

📊 4. Truth Score + Confidence Metric

Final judgment engine gives:

TRUE / FALSE / PARTIALLY SUPPORTED / UNVERIFIED

0–1 truth score

Confidence score

🖥️ 5. Modern Frontend

Streamlit-based UI:

Real-time verification

JSON inspector

Claim list view

Verdict visualization

📦 Tech Stack
Layer	Technologies
Frontend	Streamlit, Python
Backend	FastAPI, Grok API, DuckDuckGo API
Evidence Search	DuckDuckGo (Free)
LLM Reasoning	Grok: llama-3.3-70b-versatile
Hosting	Render / GitHub Codespaces
Ops	Opus Workflow automation
🏗️ Project Structure
ai-reality-engine/
│
├── backend/
│   ├── main.py            # Fact-checking API (FastAPI)
│   ├── requirements.txt
│
├── frontend/
│   ├── app.py             # Streamlit UI
│
├── render.yaml            # Render deployment config
├── README.md              # (this file)
├── AI Reality Engine.mp4  # Demo video
└── video-*.mp4            # Frontend video

⚙️ Installation & Setup
1. Clone the Repository
git clone https://github.com/HinataHamura/ai-reality-engine.git
cd ai-reality-engine

🛠️ Backend Setup (FastAPI)
Create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
.venv\Scripts\activate      # Windows

Install dependencies
pip install -r requirements.txt

Set API Keys (local)

Create .env inside /backend:

GROK_API_KEY=your_grok_api_key

Run Backend
uvicorn main:app --reload --port 8000


Backend available at:

http://localhost:8000

🖥️ Frontend Setup (Streamlit)
Install
cd frontend
pip install -r requirements.txt

Run
streamlit run app.py

🔗 Deploying on Render

Your render.yaml automatically configures:

Backend service (FastAPI)

Public URL

Health checks

Make sure BACKEND_URL in frontend is updated to:

https://your-backend.onrender.com

🧠 How the Engine Works (Pipeline)
USER TEXT
   ↓
[1] Claim Extraction (LLM)
   ↓
[2] Evidence Retrieval (DuckDuckGo)
   ↓
[3] NLI Verification (SUPPORT / CONTRADICT / NEUTRAL)
   ↓
[4] Truth Score Computation
   ↓
[5] Summary Generation
   ↓
RESULT DISPLAYED IN FRONTEND

📝 Example Input
Coffee improves life expectancy.
Pluto is a planet.
The Mediterranean diet cures cancer.

Output Example
Claim	Result	Confidence
Coffee improves life expectancy	✅ TRUE	0.80
Pluto is a planet	❌ FALSE	0.80
Mediterranean diet cures cancer	❌ FALSE	0.80
🛠 Roadmap

Planned enhancements:

🌐 Add Wikipedia API evidence

📚 Add multilingual fact-checking

🧠 Add RAG-based evidence evaluation

🔮 Add timeline verification for historical claims

📸 Add image-based claim extraction

🤝 Contributing

Contributions welcome!
Submit PRs or open issues.

🛡️ License

MIT License (or specify your preferred).

📬 Contact

Maintainer: HinataHamura
GitHub: https://github.com/HinataHamura
