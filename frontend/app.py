import os
import json
import requests
from dotenv import load_dotenv
import streamlit as st
import time

load_dotenv()

# ------------------------------------
# AUTO-DETECT BACKEND URL
# ------------------------------------
def detect_backend_url():
    codespace = os.getenv("CODESPACE_NAME")
    port = os.getenv("BACKEND_PORT", "8000")

    if codespace:
        return f"https://{codespace}-{port}.app.github.dev"

    return os.getenv("BACKEND_URL", "https://ai-reality-engine.onrender.com")


BACKEND_URL = detect_backend_url().rstrip("/")
VERIFY_ENDPOINT = f"{BACKEND_URL}/verify"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"


# ------------------------------------
# STREAMLIT CONFIG
# ------------------------------------
st.set_page_config(
    page_title="AI Reality Integrity Engine",
    layout="wide",
    page_icon="🔍"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .big-title { font-size: 38px !important; font-weight: 700 !important; }
    .section-title { font-size: 24px !important; font-weight: 600 !important; padding-top: 20px; }
    .card {
        padding: 18px 25px;
        border-radius: 12px;
        background-color: #f7f7f9;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------
# HEADER
# ------------------------------------
st.markdown("<div class='big-title'>🔍 AI Reality Integrity Engine — Frontend</div>", unsafe_allow_html=True)
st.write("Analyze text, extract factual claims, verify them, and view clean visual results.")

# ------------------------------------
# SIDEBAR
# ------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    st.text_input("Backend URL", BACKEND_URL, key="backend_url")
    st.caption("Tip: Keep this as default unless your backend URL changes.")

    if st.button("💚 Health Check"):
        try:
            r = requests.get(f"{st.session_state.backend_url}/health", timeout=10)
            st.success(f"Backend OK: {r.status_code}")
            st.json(r.json())
        except Exception as e:
            st.error(f"Health check failed: {e}")

# ------------------------------------
# MAIN INPUT UI
# ------------------------------------
left, right = st.columns([2.5, 1])

with left:
    st.markdown("<div class='section-title'>📝 Enter text to verify</div>", unsafe_allow_html=True)
    text = st.text_area("", height=220, placeholder="Paste text or claims here…")

    language = st.selectbox("🌐 Language", ["en", "es", "fr", "de"])
    user_id = st.text_input("👤 User ID (optional)")

    verify_button = st.button("🚀 Run Verification", use_container_width=True)

with right:
    st.markdown("<div class='section-title'>💡 Quick Tips</div>", unsafe_allow_html=True)
    st.markdown("""
- Focus your text → system extracts factual claims  
- Backend must be running  
- Codespaces auto-detects backend  
- Tavily API boosts evidence retrieval  
""")
    st.code("BACKEND_URL=https://YOUR-CODESPACE-8000.app.github.dev")

# ------------------------------------
# VERIFICATION PIPELINE
# ------------------------------------
if verify_button:
    if not text.strip():
        st.warning("Please enter text before verifying.")
        st.stop()

    backend_url = st.session_state.backend_url.rstrip("/")
    endpoint = f"{backend_url}/verify"

    payload = {"text": text, "user_id": user_id or None, "language": language}

    st.info("🔎 Sending request to backend…")

    start = time.time()
    with st.spinner("Analyzing text..."):
        try:
            resp = requests.post(endpoint, json=payload, timeout=120)
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    latency = round(time.time() - start, 2)

    # ---------------------------
    # ERROR HANDLING
    # ---------------------------
    if resp.status_code >= 400:
        st.error(f"Backend error: {resp.status_code}")
        try:
            st.json(resp.json())
        except:
            st.text(resp.text)
        st.stop()

    # Parse JSON
    try:
        data = resp.json()
    except:
        st.error("Invalid JSON response")
        st.text(resp.text)
        st.stop()

    # ---------------------------
    # RESULTS
    # ---------------------------
    st.success(f"✔ Verification complete! (⏱ {latency}s)")

    # ---------------------------
    # OVERALL SUMMARY
    # ---------------------------
    st.markdown("<div class='section-title'>📊 Overall Summary</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'>{data.get('overall_summary', '')}</div>", unsafe_allow_html=True)

    claims = data.get("claims", [])
    verifications = data.get("verifications", [])

    # ---------------------------
    # CLAIMS FOUND
    # ---------------------------
    st.markdown(f"<div class='section-title'>🧩 Claims Detected ({len(claims)})</div>", unsafe_allow_html=True)

    for c in claims:
        with st.expander(f"Claim {c['claim_id']} — {c['text'][:60]}..."):
            st.json(c)

    # ---------------------------
    # VERIFICATION RESULTS
    # ---------------------------
    st.markdown(f"<div class='section-title'>🔬 Verification Results ({len(verifications)})</div>", unsafe_allow_html=True)

    def verdict_color(label):
        if label == "SUPPORT":
            return "🟢 SUPPORT"
        if label == "CONTRADICT":
            return "🔴 CONTRADICT"
        return "🟡 NEUTRAL"

    for v in verifications:
        with st.expander(f"{v['claim_id']} — {verdict_color(v['label'])}"):

            st.markdown(f"### ✨ Verdict: **{v['verdict']}**")

            st.write("#### 📌 Claim:")
            st.markdown(f"> {v['claim_text']}")

            st.write("#### 📈 Confidence:")
            st.progress(min(max(float(v['confidence']), 0), 1))

            st.write("#### 📉 Score:")
            st.progress(min(max(float(v['score']), 0), 1))

            st.write("#### 🧠 Rationale:")
            st.markdown(f"<div class='card'>{v['rationale']}</div>", unsafe_allow_html=True)

            st.write("#### 🔗 Evidence Used:")
            st.json(v.get("evidence_used", []))

    # ---------------------------
    # RAW JSON
    # ---------------------------
    st.markdown("<div class='section-title'>📦 Raw Response JSON</div>", unsafe_allow_html=True)
    st.json(data)
