# app.py

import streamlit as st
import re
import html as html_escape

from agent import get_provider
from utils import generate_csv, generate_pdf
from storage import load_provider, exists
from config.urls import PROVIDERS

st.set_page_config(
    page_title="AI-Driven Healthcare Provider Information Extraction",
    page_icon="🏥",
    layout="wide"
)

def esc(value) -> str:
    if value is None:
        return ""
    return html_escape.escape(str(value))

st.markdown("""
<style>
.block-container { padding-top:1.1rem !important; padding-bottom:1.6rem !important; max-width:1180px; }

section[data-testid="stSidebar"] {
    width:340px !important; min-width:340px !important; max-width:340px !important;
    background: linear-gradient(180deg, #1a3a5c 0%, #1e4570 50%, #1a3a5c 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}
section[data-testid="stSidebar"] > div { width:340px !important; }
[data-testid="stSidebarContent"] { padding-top:1rem; padding-left:1rem; padding-right:1rem; }
section[data-testid="stSidebar"] * { color:#f0f6fc !important; }
section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color:rgba(255,255,255,0.08) !important;
    border:1px solid rgba(255,255,255,0.2) !important;
}
section[data-testid="stSidebar"] div[data-baseweb="select"] span { color:#ffffff !important; }
section[data-testid="stSidebar"] div[data-baseweb="select"] svg  { fill:#ffffff !important; }
section[data-testid="stSidebar"] .stButton > button {
    width:100%; border-radius:12px; border:none;
    background: linear-gradient(135deg, #22a06b 0%, #168f78 100%);
    color:white !important; font-weight:600; padding:0.6rem 0.9rem;
    box-shadow:0 6px 14px rgba(22,143,120,0.22);
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: linear-gradient(135deg, #1d935f 0%, #137c68 100%);
}
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMarkdown { color:#c8ddf0 !important; }
section[data-testid="stSidebar"] .stDownloadButton > button {
    width:100% !important; border-radius:10px !important;
    border:1px solid rgba(255,255,255,0.25) !important;
    background:rgba(255,255,255,0.1) !important;
    color:white !important; font-weight:600 !important;
    font-size:0.78rem !important; padding:0.45rem 0.3rem !important;
    transition:all 0.15s ease;
}
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background:rgba(255,255,255,0.22) !important;
    border-color:rgba(255,255,255,0.45) !important;
}

.sb-divider { border:none; border-top:1px solid rgba(255,255,255,0.12) !important; display:block !important; margin:0.8rem 0; }
.sb-label   { font-size:0.82rem; font-weight:700; color:#a8c8e8 !important; text-transform:uppercase; letter-spacing:0.09em; margin-bottom:0.5rem; }

.hero {
    background: linear-gradient(135deg, #f7fbff 0%, #eef7ff 100%);
    border:1px solid #e3eef8; border-radius:18px;
    padding:1.25rem 1.35rem; margin-bottom:1rem;
    box-shadow:0 6px 18px rgba(16,42,67,0.04);
}
.hero h1 { font-size:1.55rem; font-weight:700; color:#12324a !important; margin:0 0 0.3rem 0; letter-spacing:-0.02em; }
.hero p  { font-size:0.92rem; color:#4c6780; margin:0; line-height:1.55; }

.top-card {
    background:#ffffff; border:1px solid #e8edf3; border-radius:16px;
    padding:1rem; box-shadow:0 4px 14px rgba(16,42,67,0.04); margin-bottom:1rem;
}
.provider-name { font-size:1.35rem; font-weight:700; color:#14324b; line-height:1.2; }
.provider-type { font-size:0.86rem; color:#6f7d8b; margin-top:0.25rem; }
.summary-box {
    border:1px solid #d9efe7;
    background: linear-gradient(180deg, #f7fdfa 0%, #f2fbf7 100%);
    padding:0.9rem 1rem; border-radius:14px; margin-top:0.85rem;
    font-size:0.92rem; line-height:1.6; color:#24493d;
}
.metric-card {
    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    border:1px solid #e8edf3; border-radius:14px;
    padding:0.9rem 0.95rem; min-height:92px;
    box-shadow:0 3px 12px rgba(16,42,67,0.035);
}
.metric-label { font-size:0.72rem; text-transform:uppercase; letter-spacing:0.08em; color:#7a8795; margin-bottom:0.35rem; }
.metric-value { font-size:0.93rem; font-weight:600; color:#142c44; line-height:1.4; word-break:break-word; }
.metric-link  { font-size:0.9rem; font-weight:500; color:#1d5fa7; text-decoration:none; word-break:break-all; }
.section-title { font-size:1rem; font-weight:650; margin:0 0 0.8rem 0; color:#18324a; letter-spacing:-0.01em; }

.sub-card {
    background:#ffffff; border:1px solid #e8edf3; border-radius:16px;
    padding:1rem; box-shadow:0 4px 14px rgba(16,42,67,0.04); height:100%; margin-top:1rem;
}
.hours-line { font-size:0.88rem; color:#304659; padding:0.32rem 0; border-bottom:1px dashed #edf1f5; }
.hours-line:last-child { border-bottom:none; }
.ins-wrap { display:flex; flex-wrap:wrap; gap:0.4rem; }
.ins-pill {
    display:inline-block; font-size:0.76rem; padding:0.34rem 0.65rem;
    border-radius:999px; background:#eef7e8; color:#2a5a12; border:1px solid #d7ebc8;
}
.prac-card {
    background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
    border:1px solid #e8edf3; border-radius:16px;
    padding:0.95rem; margin-bottom:0.8rem;
    box-shadow:0 4px 14px rgba(16,42,67,0.04);
}
.prac-head  { display:flex; align-items:flex-start; gap:0.7rem; margin-bottom:0.5rem; }
.prac-avatar {
    width:38px; height:38px; border-radius:12px;
    background: linear-gradient(135deg, #dff5ee 0%, #eefaf6 100%);
    display:inline-flex; align-items:center; justify-content:center;
    font-size:0.8rem; font-weight:700; color:#0f6e56; flex-shrink:0;
}
.prac-name { font-size:0.9rem; font-weight:650; color:#162b3f; line-height:1.3; }
.prac-spec { font-size:0.77rem; color:#687686; margin-top:0.12rem; }
.prac-meta { margin:0.35rem 0 0.45rem 0; }
.pill { display:inline-block; font-size:0.68rem; padding:0.23rem 0.48rem; border-radius:999px; margin:0 0.28rem 0.28rem 0; border:1px solid transparent; }
.p-npi  { background:#eaf3fd; color:#195ea6; border-color:#d4e6f8; font-family:monospace; }
.p-cred { background:#f0efff; color:#574ab8; border-color:#dfdcff; }
.prac-row   { font-size:0.76rem; color:#34495e; margin-top:0.32rem; line-height:1.45; }
.prac-row b { color:#7d8794; font-weight:600; margin-right:0.3rem; }

.export-section {
    background: linear-gradient(135deg, #f0f7ff 0%, #e8f3ff 100%);
    border:1px solid #cce0f5; border-radius:16px;
    padding:1.2rem 1.3rem; margin-top:1.5rem;
    box-shadow:0 4px 14px rgba(16,42,67,0.06);
}
.export-label { font-size:0.72rem; font-weight:700; color:#4a7fa5; text-transform:uppercase; letter-spacing:0.09em; margin-bottom:0.4rem; }
.export-title { font-size:1rem; font-weight:700; color:#12324a; margin-bottom:0.2rem; }
.export-name  { font-size:0.82rem; color:#4c6780; margin-bottom:1rem; }

hr { display:none; }
</style>
""", unsafe_allow_html=True)

# ---------- Hero ----------
st.markdown("""
<div class="hero">
  <h1>🏥 Healthcare Provider Intelligence Dashboard</h1>
  <p>Structured extraction of provider details, operating hours, insurance coverage,
  practitioner profiles, NPI enrichment, ratings, and affiliations from public healthcare websites.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar — Section 1: Extract ----------
st.sidebar.markdown("<div class='sb-label' style='font-size:0.95rem;'>Select Provider</div>", unsafe_allow_html=True)
provider_name = st.sidebar.selectbox(
    "Provider", options=list(PROVIDERS.keys()),
    help="Choose a provider to load or extract data for.",
    label_visibility="collapsed",
)
force_refresh = st.sidebar.checkbox("Fetch latest information", help="Ignore cached data and re-run the full agent.")
st.sidebar.markdown("<div style='height:0.3rem'></div>", unsafe_allow_html=True)

if st.sidebar.button("Extract / Load", use_container_width=True):
    with st.spinner("Extracting Provider Information..."):
        try:
            provider = get_provider(provider_name, force_refresh=force_refresh)
            st.session_state["provider"]      = provider
            st.session_state["provider_name"] = provider_name
        except Exception as e:
            st.error(f"Extraction failed: {e}")

# ---------- Sidebar — Section 2: Export (only if providers exist) ----------
extracted_providers = [name for name in PROVIDERS.keys() if exists(name)]

if extracted_providers:
    st.sidebar.markdown("<hr class='sb-divider'>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sb-label'>⬇ Export Multiple Providers</div>", unsafe_allow_html=True)

    selected_names = []
    for name in extracted_providers:
        if st.sidebar.checkbox(name, key=f"chk_{name}"):
            selected_names.append(name)

    if selected_names:
        loaded = [prov for name in selected_names if (prov := load_provider(name))]
        if loaded:
            m1, m2 = st.sidebar.columns(2)
            with m1:
                st.download_button("⬇ CSV", data=generate_csv(loaded), file_name="providers.csv", mime="text/csv", key="mb_csv", use_container_width=True)
            with m2:
                st.download_button("⬇ PDF", data=generate_pdf(loaded), file_name="providers.pdf", mime="application/pdf", key="mb_pdf", use_container_width=True)
    else:
        st.sidebar.markdown("<div style='font-size:0.78rem;color:#a8c8e8;'>Check providers above to export.</div>", unsafe_allow_html=True)

# ---------- Gate ----------
if "provider" not in st.session_state:
    st.info("👈 Select a provider and click **Extract / Load** to begin.")
    st.stop()

p             = st.session_state["provider"]
provider_name = st.session_state.get("provider_name", "provider")

# ---------- Provider Card ----------
summary_html = f'<div class="summary-box">{esc(p.summary)}</div>' if getattr(p, "summary", None) else ""
st.markdown(f"""
    <div class="top-card">
        <div class="provider-name">{esc(p.name) or "Unknown Provider"}</div>
        <div class="provider-type">{esc(p.facility_type) or "Facility type not listed"}</div>
        {summary_html}
    </div>
""", unsafe_allow_html=True)

# ---------- Metrics ----------
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Address</div><div class="metric-value">{esc(getattr(p,"address","")) or "—"}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Contact</div><div class="metric-value">{esc(getattr(p,"contact","")) or "—"}</div></div>', unsafe_allow_html=True)
with c3:
    w            = getattr(p, "website", None)
    website_html = f"<a class='metric-link' href='{esc(w)}' target='_blank'>{esc(w)}</a>" if w else "<div class='metric-value'>—</div>"
    st.markdown(f'<div class="metric-card"><div class="metric-label">Website</div>{website_html}</div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="metric-card"><div class="metric-label">Rating / Review</div><div class="metric-value">{esc(getattr(p,"rating","")) or "—"}</div></div>', unsafe_allow_html=True)

# ---------- Hours + Insurance ----------
h_col, i_col = st.columns(2)
with h_col:
    hours_html = f"<div class='hours-line'>{esc(getattr(p,'operating_hours',''))}</div>" if getattr(p,"operating_hours",None) else "<div class='metric-value'>—</div>"
    st.markdown(f'<div class="sub-card"><div class="section-title">Operating Hours</div>{hours_html}</div>', unsafe_allow_html=True)
with i_col:
    ins           = getattr(p, "accepted_insurances", None)
    insurance_html = "<div class='ins-wrap'>" + "".join(f"<span class='ins-pill'>{esc(i)}</span>" for i in ins) + "</div>" if ins else "<div class='metric-value'>—</div>"
    st.markdown(f'<div class="sub-card"><div class="section-title">Accepted Insurance</div>{insurance_html}</div>', unsafe_allow_html=True)

# ---------- Affiliations ----------
if getattr(p, "affiliations", None):
    st.markdown(f"""
        <div class="top-card" style="margin-top:1rem;">
            <div class="section-title" style="margin-bottom:0.35rem;">Affiliations</div>
            <div class="metric-value" style="font-weight:500;">{esc(p.affiliations)}</div>
        </div>
    """, unsafe_allow_html=True)

# ---------- Practitioners ----------
practitioners = getattr(p, "practitioners", []) or []
st.markdown(f"<div class='section-title' style='margin-top:1rem;'>Practitioners ({len(practitioners)})</div>", unsafe_allow_html=True)

if not practitioners:
    st.info("No practitioners found.")
else:
    for row in [practitioners[i:i+3] for i in range(0, len(practitioners), 3)]:
        cols = st.columns(3)
        for col, prac in zip(cols, row):
            with col:
                full_name   = str(getattr(prac, "full_name", "") or "")
                parts       = full_name.replace("Dr.", "").replace("Dr ", "").strip().split()
                initials    = (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else "?"
                npi_pill    = f"<span class='pill p-npi'>NPI {esc(prac.npi_number)}</span>" if getattr(prac,"npi_number",None) else ""
                cred_pill   = f"<span class='pill p-cred'>{esc(prac.qualification_certification)}</span>" if getattr(prac,"qualification_certification",None) else ""
                contact_row = f"<div class='prac-row'><b>Contact</b> {esc(getattr(prac,'contact_details',''))}</div>" if getattr(prac,"contact_details",None) else ""
                hours_row   = f"<div class='prac-row'><b>Hours</b> {esc(re.sub(r'<[^>]+>','',str(getattr(prac,'office_hour',''))))}</div>" if getattr(prac,"office_hour",None) else ""
                st.markdown(f"""
                    <div class="prac-card">
                        <div class="prac-head">
                            <div class="prac-avatar">{esc(initials)}</div>
                            <div>
                                <div class="prac-name">{esc(full_name) or "Unknown"}</div>
                                <div class="prac-spec">{esc(getattr(prac,"speciality","")) or "Specialty not listed"}</div>
                            </div>
                        </div>
                        <div class="prac-meta">{npi_pill}{cred_pill}</div>
                        {contact_row}{hours_row}
                    </div>
                """, unsafe_allow_html=True)

# ---------- Export ----------
st.markdown(f"""
    <div class='export-section'>
        <div class='export-label'>Export</div>
        <div class='export-title'>Download Current Provider</div>
        <div class='export-name'>{esc(p.name)}</div>
    </div>
""", unsafe_allow_html=True)
b1, b2 = st.columns(2)
with b1:
    st.download_button("⬇ Download CSV", data=generate_csv([p]), file_name=f"{provider_name}.csv", mime="text/csv", key="dl_single_csv", use_container_width=True)
with b2:
    st.download_button("⬇ Download PDF", data=generate_pdf([p]), file_name=f"{provider_name}.pdf", mime="application/pdf", key="dl_single_pdf", use_container_width=True)