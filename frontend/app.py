import os
import json
import requests
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

# ---------------------------
# AUTO-DETECT BACKEND URL
# ---------------------------
def detect_backend_url():
    """
    Detect backend URL automatically.
    - If in GitHub Codespaces → build the forwarded URL automatically
    - Else → use BACKEND_URL from .env or fallback to localhost
    """
    codespace = os.getenv("CODESPACE_NAME")
    port = os.getenv("BACKEND_PORT", "8000")

    if codespace:
        return f"https://{codespace}-{port}.app.github.dev"

    return os.getenv("BACKEND_URL", "http://localhost:8000")


BACKEND_URL = detect_backend_url().rstrip("/")
VERIFY_ENDPOINT = f"{BACKEND_URL}/verify"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"


# ---------------------------
# STREAMLIT PAGE SETTINGS
# ---------------------------
st.set_page_config(
    page_title="AI Reality Integrity Engine — Frontend",
    layout="wide"
)

st.title("AI Reality Integrity Engine — Frontend")
st.markdown(
    "Paste a piece of text and click **Verify** to run the fact-checking pipeline. "
    "The frontend calls your backend `/verify` endpoint and displays claims, verdicts, evidence, and the raw response."
)

# ---------------------------
# SIDEBAR SETTINGS
# ---------------------------
with st.sidebar:
    st.header("Settings")
    st.text_input("Backend URL", value=BACKEND_URL, key="backend_url")
    st.caption("If you change the backend URL, press **Verify** to use it.")

# ---------------------------
# HEALTH CHECK BUTTON
# ---------------------------
if st.button("Health check backend"):
    backend_url = st.session_state.get("backend_url", BACKEND_URL).rstrip("/")
    try:
        r = requests.get(f"{backend_url}/health", timeout=10)
        st.success(f"Backend responded: {r.status_code}")
        try:
            st.json(r.json())
        except:
            st.write(r.text)
    except Exception as e:
        st.error(f"Health check failed: {e}")

st.markdown("---")

# ---------------------------
# MAIN INPUT AREA
# ---------------------------
col1, col2 = st.columns([2, 1])

with col1:
    text = st.text_area("Text to verify", height=250, placeholder="Paste text or claims here...")
    language = st.selectbox("Language", ["en", "es", "fr", "de"], index=0)
    user_id = st.text_input("User ID (optional)", placeholder="user identifier")
    verify_button = st.button("Verify")

with col2:
    st.subheader("Quick tips")
    st.markdown("""
    - Keep text focused → the system extracts factual claims.
    - Ensure your backend is running.
    - If using GitHub Codespaces, backend URL is auto-detected.
    - Evidence retrieval requires Tavily API key (optional).
    """)
    st.code("BACKEND_URL=https://YOUR-CODESPACE-8000.app.github.dev")

# ---------------------------
# VERIFY PIPELINE EXECUTION
# ---------------------------
if verify_button:
    backend_url = st.session_state.get("backend_url", BACKEND_URL).rstrip("/")
    endpoint = f"{backend_url}/verify"

    if not text.strip():
        st.warning("Please enter some text.")
        st.stop()

    payload = {
        "text": text,
        "user_id": user_id or None,
        "language": language
    }

    st.info("Sending request to backend...")
    with st.spinner("Running verification pipeline..."):

        try:
            resp = requests.post(endpoint, json=payload, timeout=120)
        except Exception as e:
            st.error(f"Request failed: {e}")
            st.stop()

    if resp.status_code >= 400:
        st.error(f"Backend error: {resp.status_code}")
        try:
            st.json(resp.json())
        except:
            st.text(resp.text)
        st.stop()

    # ---------------------------
    # PARSE RESPONSE
    # ---------------------------
    try:
        data = resp.json()
    except Exception as e:
        st.error(f"Invalid JSON response: {e}")
        st.text(resp.text)
        st.stop()

    # ---------------------------
    # DISPLAY RESULTS
    # ---------------------------
    st.success("Verification complete!")

    st.subheader("Overall Summary")
    st.write(data.get("overall_summary", ""))

    claims = data.get("claims", [])
    verifications = data.get("verifications", [])

    # CLAIMS
    st.subheader(f"Claims Found ({len(claims)})")
    for c in claims:
        with st.expander(f"Claim {c.get('claim_id')}"):
            st.json(c)

    # VERDICTS
    st.subheader(f"Verification Results ({len(verifications)})")
    for v in verifications:
        label = v.get("label", "unknown")
        with st.expander(f"{v.get('claim_id')} → {v.get('verdict')} ({label})"):
            st.markdown(f"**Claim:** {v.get('claim_text')}")
            st.markdown(f"**Verdict:** {v.get('verdict')}")
            st.markdown(f"**Score:** {v.get('score')}")
            st.markdown(f"**Confidence:** {v.get('confidence')}")
            st.markdown("**Rationale:**")
            st.write(v.get("rationale"))
            st.markdown("**Evidence:**")
            st.json(v.get("evidence_used", []))

    # RAW JSON
    st.subheader("Raw Response JSON")
    st.json(data)
