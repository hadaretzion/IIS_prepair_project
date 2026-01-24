import os
import requests
import streamlit as st

# Simple Streamlit client for the PrepAIr backend.
# Backend base URL (default to local dev)
DEFAULT_BACKEND_URL = os.getenv("BACKEND_URL") or os.getenv("VITE_BACKEND_URL") or "http://localhost:8000"

st.set_page_config(page_title="PrepAIr Streamlit", layout="wide")

# Apply a dark, glassy theme to resemble the main app
st.markdown(
        """
        <style>
        :root {
            --bg: #0f111a;
            --card: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.08);
            --text: #e8ecf5;
            --muted: #cbd5e1;
            --accent: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        }
        body, .main, .block-container {background: var(--bg) !important; color: var(--text) !important;}
        .block-container {padding-top: 2rem;}
        .stMarkdown, .stTextInput label, .stTextArea label, .stHeader, .stSubheader {color: var(--text) !important;}
        .stTextInput > div > input, .stTextArea textarea {
            background: var(--card) !important;
            color: var(--text) !important;
            border: 1px solid var(--border) !important;
        }
        .stButton button {
            background: var(--accent) !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            padding: 0.5rem 1.2rem !important;
        }
        .stExpander {
            background: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
        }
        .stMetric {
            background: var(--card) !important;
            padding: 0.5rem 0.8rem !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
)

# --- Helpers -----------------------------------------------------------------

def api_request(method: str, backend_url: str, path: str, **kwargs):
    url = backend_url.rstrip("/") + path
    try:
        resp = requests.request(method, url, timeout=60, **kwargs)
        resp.raise_for_status()
        if resp.text:
            return resp.json()
        return None
    except requests.HTTPError as http_err:
        detail = None
        try:
            detail = resp.json().get("detail") if resp is not None else None
        except Exception:
            detail = None
        raise RuntimeError(detail or str(http_err)) from http_err
    except Exception as err:
        raise RuntimeError(str(err)) from err


def ensure_user(backend_url: str, user_id: str | None):
    payload = {"user_id": user_id or ""}
    data = api_request("post", backend_url, "/api/users/ensure", json=payload)
    return data["user_id"]


def ingest_cv(backend_url: str, user_id: str, cv_text: str):
    payload = {"user_id": user_id, "cv_text": cv_text}
    data = api_request("post", backend_url, "/api/cv/ingest", json=payload)
    return data["cv_version_id"]


def ingest_jd(backend_url: str, user_id: str, jd_text: str):
    payload = {"user_id": user_id, "jd_text": jd_text}
    data = api_request("post", backend_url, "/api/jd/ingest", json=payload)
    return data["job_spec_id"]


def analyze_cv(backend_url: str, user_id: str, cv_version_id: str, job_spec_id: str):
    payload = {
        "user_id": user_id,
        "cv_version_id": cv_version_id,
        "job_spec_id": job_spec_id,
    }
    return api_request("post", backend_url, "/api/cv/analyze", json=payload)


def get_history(backend_url: str, user_id: str):
    return api_request("get", backend_url, f"/api/interview/history/{user_id}")


# --- UI ----------------------------------------------------------------------

st.title("PrepAIr (Streamlit client)")

with st.sidebar:
    backend_url = st.text_input("Backend URL", value=DEFAULT_BACKEND_URL)
    st.caption("Backend should be the FastAPI server (default http://localhost:8000)")

if "user_id" not in st.session_state:
    st.session_state["user_id"] = ""

# --- Ensure User -------------------------------------------------------------
with st.expander("1) User", expanded=True):
    st.write("We need a user ID (UUID). Click ensure to create one if empty.")
    col_user1, col_user2 = st.columns([3, 1])
    with col_user1:
        user_id_input = st.text_input("User ID", value=st.session_state["user_id"], key="user_id_input")
    with col_user2:
        if st.button("Ensure User"):
            try:
                uid = ensure_user(backend_url, user_id_input.strip() or None)
                st.session_state["user_id"] = uid
                st.success(f"User ensured: {uid}")
            except Exception as e:
                st.error(f"User ensure failed: {e}")

# --- CV & JD Analysis --------------------------------------------------------
st.markdown("---")
st.header("Analyze CV vs Job Description")

cv_text = st.text_area("CV Text", height=180, placeholder="Paste your CV text here")
jd_text = st.text_area("Job Description", height=180, placeholder="Paste the JD here")

if st.button("Run Analysis", type="primary"):
    if not cv_text or not jd_text:
        st.warning("Please provide both CV and JD text.")
    else:
        try:
            # Ensure user
            uid = ensure_user(backend_url, st.session_state.get("user_id") or None)
            st.session_state["user_id"] = uid

            with st.spinner("Ingesting CV..."):
                cv_version_id = ingest_cv(backend_url, uid, cv_text)
            with st.spinner("Ingesting JD..."):
                job_spec_id = ingest_jd(backend_url, uid, jd_text)
            with st.spinner("Analyzing..."):
                analysis = analyze_cv(backend_url, uid, cv_version_id, job_spec_id)

            st.success("Analysis complete")
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Match Score", f"{analysis.get('match_score',0)*100:.0f}%")
            strengths = analysis.get("strengths", [])
            gaps = analysis.get("gaps", [])
            suggestions = analysis.get("suggestions", [])

            st.subheader("Strengths")
            st.write(strengths or "-")
            st.subheader("Gaps")
            st.write(gaps or "-")
            st.subheader("Suggestions")
            st.write(suggestions or "-")
        except Exception as e:
            st.error(f"Analysis failed: {e}")

# --- Interview History -------------------------------------------------------
st.markdown("---")
st.header("Interview History")
st.caption("Displays past interviews for the given user_id")

history_user = st.text_input("User ID for history", value=st.session_state.get("user_id", ""))

if st.button("Load History"):
    if not history_user:
        st.warning("Enter a user_id to fetch history.")
    else:
        try:
            data = get_history(backend_url, history_user.strip())
            interviews = data.get("interviews") or []
            if not interviews:
                st.info("No interviews found.")
            for sess in interviews:
                title = sess.get("role_title", "(untitled)")
                created = sess.get("created_at", "")
                score = sess.get("average_score", 0)
                label = f"{title} • {created} • {score:.1f}%"
                with st.expander(label):
                    st.write(sess)
        except Exception as e:
            st.error(f"History fetch failed: {e}")

# --- Footer ------------------------------------------------------------------
st.markdown("---")
st.caption("Streamlit client for PrepAIr FastAPI backend. Ensure backend is running on the URL above.")
