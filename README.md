# AI-Driven Healthcare Provider Information Extraction
An AI agent that automatically collects and structures detailed information
about healthcare providers from publicly available online sources.

---
## Project Overview
This system uses a LangGraph ReAct agent to orchestrate multiple data collection
tools and extract structured information about healthcare providers including
facility details, practitioners, NPI numbers, insurance, ratings, and affiliations.

---
## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    app.py (Streamlit UI)                    │
│                            │                                │
│                  get_provider(name)                         │
│                            │                                │
│                  ┌─────────▼─────────┐                      │
│                  │     agent.py      │                      │
│                  │  ReAct Agent      │                      │
│                  │   (GPT-4o)        │                      │
│                  └──┬───┬───┬───┬────┘                      │
│                     │   │   │   │                           │
│          ┌──────────┘   │   │   └──────────┐                │
│          ▼              ▼   ▼              ▼                │
│  scrape_websites  ddgs_search  llm_search  get_npi_data     │
│  (BeautifulSoup)   (free)     (fallback)  (NPPES API)       │
│          └──────────────┴───┴──────────────┘                │
│                            │                                │
│                  _llm_parse (GPT-4o)                        │
│                  structured output                          │
│                            │                                │
│                  HealthcareProvider                         │
│                  (Pydantic model)                           │
│                            │                                │
│                  storage/providers.json                     │
└─────────────────────────────────────────────────────────────┘
```
---

## Data Flow

```
scrape_websites   → fetches provider website pages (BeautifulSoup)
        ↓
search_web_ddgs   → fills gaps: ratings, insurance, affiliations (free)
        ↓ (only if scraping fails entirely)
search_web_llm    → full LLM web search (last resort, costs $)
        ↓
get_npi_data      → extracts practitioner names → queries NPPES API
        ↓
_llm_parse        → GPT-4o structured extraction → HealthcareProvider
        ↓
save_provider     → cached to storage/providers.json
```

---

## Why Agent Design Over a Fixed Pipeline

### Fixed Pipeline Limitations
A fixed pipeline always runs every step regardless of what data was already
collected. If scraping returns complete data, a pipeline would still call
DuckDuckGo and LLM search unnecessarily — wasting time and cost.

### ReAct Agent Advantages
The LangGraph ReAct agent evaluates results after each tool call and decides
what to do next based on what is still missing:

- If scraping returns full data → skips search tools entirely
- If ratings/insurance are missing → calls DuckDuckGo only
- If scraping fails (404/blocked) → falls back to LLM search
- Always calls NPI lookup last with complete accumulated content

### Cost Control Strategy
```
- Free:  scrape_websites + search_web_ddgs + NPPES API
- Paid:  search_web_llm  — only when scraping fails completely
- Paid: llm/agent (Open AI API)
```
---

## Information Extracted

### Provider / Organization Details
- Full name and facility type
- Address (street, city, state, ZIP)
- Contact phone and/or email
- Operating hours
- Website URL
- Introduction / summary

### Practitioner Information
- Full name and qualification (MD, DO, NP)
- Specialty (from NPPES primary taxonomy)
- NPI number (from NPPES registry)
- Certifications (from NPPES secondary taxonomies)
- Contact details and availability

### Additonal Fields
- Accepted insurance plans
- Patient ratings or review summary
- Hospital or network affiliations

---

## Tech Stack

| Component             | Technology                               |
|-----------------------|------------------------------------------|
| Agent orchestration   | LangGraph ReAct + GPT-4o                 |
| Web scraping          | requests + BeautifulSoup                 |
| Targeted search       | DuckDuckGo (duckduckgo-search)           |
| LLM web search        | OpenAI Responses API (fallback only)     |
| NPI lookup            | NPPES Public API (free, no key needed)   |
| Structured extraction | GPT-4o structured outputs (Pydantic v2)  |
| Caching               | Local JSON file                          |
| UI                    | Streamlit                                |
| Export                | CSV (built-in), PDF (fpdf)               |

---

## Project Structure
```
├── agent.py            # Main entrypoint — ReAct agent + extraction
├── tools.py            # LangChain tools (scrape, search, NPI)
├── utils.py            # Web fetching, NPPES, LLM parse, CSV/PDF export
├── data_models.py      # Pydantic models (HealthcareProvider, Practitioner)
├── storage.py          # JSON cache read/write
├── app.py              # Streamlit UI
├── config/
│   └── urls.py         # Provider name → URL mapping + NPPES URL
├── storage/
│   └── providers.json  # Auto-created on first extraction
├── requirements.txt
└── .env                # OPENAI_API_KEY (not commited to git)
```
---

## Setup

```bash
# 1. Clone repository
git clone <repo-url>
cd "AI-Driven Healthcare Provider Information Extraction"

# 2. Create virtual environment (Python 3.13)
python3.13 -m venv hipe
source hipe/bin/activate        # Mac/Linux
hipe\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
# create .env and add your OpenAI API key:
# OPENAI_API_KEY=sk-...

# 5. Run agent directly (terminal testing)
python agent.py

# 6. Run Streamlit UI
streamlit run app.py
```
---

## Storage Design & Assumptions

Provider data is stored locally in `storage/providers.json`:

```json
{
  "Soin Medical Center": {
    "name": "Soin Medical Center",
    "facility_type": "Hospital",
    "address": "3535 Pentagon Blvd, Beavercreek, OH 45431",
    ...
  }
}
```

**Assumptions:**
- Provider data does not change frequently — local JSON is sufficient
  for this project scope of 2-3 providers
- The storage interface (`save_provider`, `load_provider`, `exists`) is
  intentionally simple and swappable — replace `storage.py` to use
  Other storage options without changing `agent.py` or `app.py`
- `force_refresh=True` bypasses cache and re-extracts at any time
- `storage/providers.json` is auto-created on first extraction

---

## Adding a New Provider

Open `config/urls.py` and add the provider name and URLs:

```python
PROVIDERS = {
    "Soin Medical Center": [
        "https://ketteringhealth.org/locations/soin-medical-center/",
        "https://ketteringhealth.org/locations/soin-medical-center/doctors/",
    ],
    # Add new provider here:
    "Your Provider Name": [
        "https://www.yourprovider.com/",
        "https://www.yourprovider.com/doctors",
    ],
}
```

**Tips for choosing URLs:**
- Always include the homepage
- Include a dedicated doctors/providers page — most important for NPI lookup
- Include a services or specialties page if available
- Avoid login-protected or JavaScript-rendered pages

---

## Design Decisions & Assumptions

### Why scraping over search-only?
Provider websites contain the most complete and accurate structured data —
full practitioner lists, exact hours, insurance tables. DuckDuckGo snippets
are insufficient for structured extraction. Scraping known URLs is more
reliable and cheaper than searching.

### Why DuckDuckGo for ratings/insurance/affiliations?
These fields rarely appear cleanly on provider websites but appear frequently
in third-party sources. DuckDuckGo is free, requires no API key, and returns
sufficient snippet data for these targeted fields. It is not used as a full
scraping fallback because snippets are too short to recover complete provider
details.

### Why LLM web search only as last resort?
LLM web search costs money per call. It is only necessary when scraping fails
entirely. DuckDuckGo handles targeted gap-filling for free. This design
minimizes API cost while maintaining resilience.

### Why NPPES for NPI numbers?
NPPES is the official federal registry for National Provider Identifiers.
It guarantees verified NPI numbers, credentials, license numbers, and
taxonomy classifications directly from the source.

### Why local JSON cache?
For a 2-3 provider scope, a database adds unnecessary complexity. The JSON
file is human-readable and portable. The storage interface is designed to be
swappable without touching any other file.

---

## Limitations & Future Improvements

| Limitation | Future Improvement |
|---|---|
| Providers configured manually in `urls.py` | Dynamic provider discovery via web search |
| NPI name matching can miss name variants | Fuzzy matching with confidence scoring |
| No cache — stale data needs manual refresh | Add scheduled re-extraction |
| DuckDuckGo has undocumented rate limits | Add retry logic |
| Local JSON storage | Swap `storage.py` for other datases |
| Single-user Streamlit app | Multi-user support with session isolation |