# utils.py

import os,io,csv
import logging as log
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
from fpdf import FPDF
from concurrent.futures import ThreadPoolExecutor
from data_models import HealthcareProvider

from openai import OpenAI
import warnings


load_dotenv()
log.basicConfig(level=log.INFO)
warnings.filterwarnings("ignore", category=ResourceWarning)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FIELDNAMES = [
    "provider_name", "facility_type", "address", "contact",
    "operating_hours", "website", "accepted_insurances",
    "affiliations", "summary", "rating",
    "practitioner_full_name", "speciality", "npi_number",
    "qualification_certification", "contact_details", "office_hour",
]
def _extract_text(html: str) -> str:
    """
    Strip HTML tags and return only visible text.
    Removes scripts, styles noise.
    Keeps meaningful content for LLM model(GPT).
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    
    texts = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "a"]):
        text = tag.get_text(strip=True)
        if tag.name == "a" and tag.get("href"):
            text = f"{text} ({tag.get('href')})"
        if text:
            texts.append(text)

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cols = [col.get_text(strip=True) for col in row.find_all(["td", "th"])]
            cols = [c for c in cols if c]

            if cols:
                # Join row into readable format
                texts.append(" | ".join(cols))

    return "\n".join(texts)

def fetch_all_sync(urls: list[str], provider_name: str = "") -> str:
    """Fetch all URLs concurrently using threads and return combined text."""

    def _one(url: str) -> str:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                text = _extract_text(r.text)
                label = f"{provider_name}_" if provider_name else ""
                domain = urlparse(url).netloc.replace("www.", "")
                return f"=== {label}{domain} ===\n{text}" if text else ""
            log.info(f"[fetcher] {url} -> status {r.status_code}")
            return ""
        except Exception as e:
            log.error(f"[fetcher] failed {url}: {e}")
            return ""

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_one, urls))

    return "\n\n".join(r for r in results if r)


def fetch_all_npis_sync(nppes_url: str, practitioners: list) -> dict[str, dict]:
    """Fetch NPI records for all practitioners concurrently."""

    def _one(p) -> tuple[str, dict]:
        full_name = f"{p.first_name} {p.last_name}"
        try:
            r = requests.get(
                nppes_url,
                params={
                    "version":    "2.1",
                    "first_name": p.first_name,
                    "last_name":  p.last_name,
                    "state":      p.state,
                    "limit":      3,
                },
                timeout=30,
            )
            data = r.json()
            results = data.get("results", [])
            return full_name, results[0] if results else {}
        except Exception as e:
            log.error(f"[nppes] error for '{full_name}': {e}")
            return full_name, {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        pairs = list(pool.map(_one, practitioners))

    return dict(pairs)

# LLM helper
def _llm_parse(system: str, user: str, output_format):
    """Run a single structured LLM call and return the parsed Pydantic object."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        response_format=output_format,
    )
    return response.choices[0].message.parsed


# CSV
def _provider_base_row(p: HealthcareProvider) -> dict:
    """Extract provider-level fields into a flat dict."""
    return {
        "provider_name":        getattr(p, "name", "") or "",
        "facility_type":        getattr(p, "facility_type", "") or "",
        "address":              getattr(p, "address", "") or "",
        "contact":              getattr(p, "contact", "") or "",
        "operating_hours":      getattr(p, "operating_hours", "") or "",
        "website":              getattr(p, "website", "") or "",
        "accepted_insurances":  "; ".join(getattr(p, "accepted_insurances", []) or []),
        "affiliations":         getattr(p, "affiliations", "") or "",
        "summary":              getattr(p, "summary", "") or "",
        "rating":               getattr(p, "rating", "") or "",
    }

def generate_csv(providers: list[HealthcareProvider]) -> bytes:
    """Generate CSV for one or more providers."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDNAMES)
    writer.writeheader()

    for p in providers:
        base = _provider_base_row(p)
        practitioners = getattr(p, "practitioners", []) or []

        if practitioners:
            for prac in practitioners:
                writer.writerow({
                    **base,
                    "practitioner_full_name":       getattr(prac, "full_name", "") or "",
                    "speciality":                   getattr(prac, "speciality", "") or "",
                    "npi_number":                   getattr(prac, "npi_number", "") or "",
                    "qualification_certification":  getattr(prac, "qualification_certification", "") or "",
                    "contact_details":              getattr(prac, "contact_details", "") or "",
                    "office_hour":                  getattr(prac, "office_hour", "") or "",
                })
        else:
            writer.writerow({
                **base,
                "practitioner_full_name": "",
                "speciality": "", "npi_number": "",
                "qualification_certification": "",
                "contact_details": "", "office_hour": "",
            })

    return buf.getvalue().encode("utf-8")


# PDF 
def _clean(text) -> str:
    """Sanitize text for PDF latin-1 encoding — replace non-latin chars."""
    text = str(text or "")
    replacements = {
        "\u2013": "-",    # en dash
        "\u2014": "-",    # em dash
        "\u2018": "'",    # left single quote
        "\u2019": "'",    # right single quote (CNP's issue)
        "\u201c": '"',    # left double quote
        "\u201d": '"',    # right double quote
        "\u2022": "-",    # bullet
        "\u00b7": "-",    # middle dot
        "\u00ae": "(R)",  # registered trademark
        "\u00a9": "(C)",  # copyright
        "\u2122": "(TM)", # trademark
        "\u00e2": "a",    # â
        "\u00e9": "e",    # é
        "\u00e8": "e",    # è
        "\u00e0": "a",    # à
        "\u2026": "...",  # ellipsis
        "\u00a0": " ",    # non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text.encode("latin-1", "replace").decode("latin-1")

def _pdf_section_title(pdf: FPDF, title: str):
    pdf.set_font("Arial", "B", 12)
    pdf.set_fill_color(230, 240, 250)
    pdf.cell(0, 8, _clean(title), ln=True, fill=True)
    pdf.ln(1)

def _pdf_field(pdf: FPDF, label: str, value):
    pdf.set_font("Arial", "B", 10)
    pdf.cell(45, 7, f"{label}:", ln=False)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 7, _clean(value))

def generate_pdf(providers: list[HealthcareProvider]) -> bytes:
    """Generate PDF for one or more providers."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    for p in providers:
        pdf.add_page()

        # ── Header ──
        pdf.set_font("Arial", "B", 18)
        pdf.cell(0, 12, _clean(p.name), ln=True)
        pdf.set_font("Arial", "I", 11)
        pdf.cell(0, 7, _clean(getattr(p, "facility_type", "")), ln=True)
        pdf.ln(3)

        # ── Summary ──
        if getattr(p, "summary", None):
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 6, _clean(p.summary))
            pdf.ln(3)

        # ── Provider Details ──
        _pdf_section_title(pdf, "Provider Details")
        fields = [
            ("Address",      getattr(p, "address", "")),
            ("Contact",      getattr(p, "contact", "")),
            ("Hours",        getattr(p, "operating_hours", "")),
            ("Website",      getattr(p, "website", "")),
            ("Insurance",    "; ".join(getattr(p, "accepted_insurances", []) or [])),
            ("Rating",       getattr(p, "rating", "")),
            ("Affiliations", getattr(p, "affiliations", "")),
        ]
        for label, value in fields:
            _pdf_field(pdf, label, value)
        pdf.ln(4)

        # ── Practitioners ──
        practitioners = getattr(p, "practitioners", []) or []
        if practitioners:
            _pdf_section_title(pdf, f"Practitioners ({len(practitioners)})")
            for prac in practitioners:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 7, _clean(getattr(prac, "full_name", "")), ln=True)
                prac_fields = [
                    ("Specialty",      getattr(prac, "speciality", "")),
                    ("NPI",            getattr(prac, "npi_number", "")),
                    ("Qualification",  getattr(prac, "qualification_certification", "")),
                    ("Contact",        getattr(prac, "contact_details", "")),
                    ("Availability",   getattr(prac, "office_hour", "")),
                ]
                for label, value in prac_fields:
                    _pdf_field(pdf, f"  {label}", value)
                pdf.ln(2)

    return pdf.output(dest="S").encode("latin-1")