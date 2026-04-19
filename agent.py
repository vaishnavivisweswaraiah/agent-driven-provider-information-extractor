# agent.py

import json
import warnings
import logging as log
from dotenv import load_dotenv
import os
from datetime import datetime

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage

from storage import load_provider, save_provider, exists
from tools import scrape_websites, search_web_llm, get_npi_data, search_web_ddgs, PROVIDERS
from utils import _llm_parse
from data_models import HealthcareProvider


load_dotenv()
log.basicConfig(level=log.INFO)
# Ignore all DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Ignore all ResourceWarnings
warnings.filterwarnings("ignore", category=ResourceWarning)

_AGENT_SYSTEM_PROMPT ="""You are a Healthcare Provider Information expert and also data collection assistant.
Collect complete information for ALL fields:
provider name, facility type, address, contact, hours, website, accepted insurance, ratings, affiliations.
practitioners with NPI numbers, qualification, certification, office hours or appointment only """

_EXTRACTION_SYSTEM_PROMPT = (
    "You are a Healthcare Provider Information expert and also data collection assistant"
    "Only use what is explicitly present — never invent data."
)

_EXTRACTION_USER_PROMPT = """Extract all available structured information from the content below.

Provider fields:
  - Full name of the healthcare provider or organization
  - Introduction or general summary (not a rating summary)
  - Facility type (clinic, hospital, specialty practice, etc.)
  - Address (street, city, state, ZIP)
  - Contact phone number and/or email
  - Operating hours
  - Website URL (home page only)
  - Accepted insurance plans
  - Patient rating (average) OR review summary
  - Affiliations (look for: 'member of', 'part of', 'affiliated with')

For each practitioner:
  - Full name without any titles or suffixes appended
  - Specialty from NPPES taxonomies where primary=true, use 'desc'
  - NPI number from NPPES 'number' field
  - Qualification (e.g. MD, DO, NP) and Certifications of the practioner
  - Contact details if available
  - Office hours or appointment availability

Replace all missing or null values with 'Not available'

CONTENT:
{context}"""

def _invoke_agent(provider_name: str) -> str:
    """Run the ReAct agent and return combined raw content from all tool calls."""
    agent = create_agent(
        model  = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")),
        tools  = [scrape_websites, search_web_ddgs, search_web_llm, get_npi_data],
        system_prompt= SystemMessage(content=_AGENT_SYSTEM_PROMPT),
    )

    result = agent.invoke(
    {"messages": [("user", f"Collect all information about '{provider_name}'.")]},
    config={"recursion_limit": 25,"callbacks": [], "verbose": True})

    # Separate scraped content from NPPES data
    collected  = []
    nppes_data = {}

    for msg in result.get("messages", []):
        if not isinstance(msg, ToolMessage):
            continue
        if msg.name in ("scrape_websites", "search_web_llm", "search_web_ddgs"):
            collected.append(str(msg.content))
        elif msg.name == "get_npi_data":
            try:
                nppes_data = json.loads(msg.content)
            except Exception:
                log.warning("[agent] failed to parse get_npi_data response")

    raw_content = "\n\n".join(collected)
    if not raw_content:
        raise ValueError(f"[agent] no content collected for '{provider_name}'")

    log.info(f"[agent] raw content: {len(raw_content)} chars | NPPES: {sum(1 for v in nppes_data.values() if v)}/{len(nppes_data)} matched")

    return f"WEBSITE:\n{raw_content}\n\nNPPES:\n{json.dumps(nppes_data, indent=2)}"

def get_provider(provider_name: str, force_refresh: bool = False) -> HealthcareProvider:
    """
    Main entrypoint. Returns a fully populated HealthcareProvider object.
    Uses cached result if available. Set force_refresh=True to re-extract.
    """
    # Return cache if available
    if not force_refresh and exists(provider_name):
        log.info(f"[agent] returning cached result for '{provider_name}'")
        cached = load_provider(provider_name)
        if cached:
            return cached
        log.warning(f"[agent] cache returned None for '{provider_name}' — re-extracting")

    if provider_name not in PROVIDERS:
        raise ValueError(f"'{provider_name}' not found in config/urls.py")

    # Collect raw content via agent
    context = _invoke_agent(provider_name)

    # Extract structured data
    provider = _llm_parse(
        system        = _EXTRACTION_SYSTEM_PROMPT,
        user          = _EXTRACTION_USER_PROMPT.format(context=context),
        output_format = HealthcareProvider,
    )
    save_provider(provider_name, provider)
    log.info(f"[agent] done — {len(provider.practitioners)} practitioners saved")
    return provider

if __name__ == "__main__":
    provider = get_provider("Centerpoint Health", True)
    print(json.dumps(provider.model_dump(), indent=2))
