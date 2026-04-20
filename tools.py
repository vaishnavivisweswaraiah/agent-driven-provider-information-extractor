# tools.py

import os
import json
import asyncio
import logging as log
from dotenv import load_dotenv

from openai import OpenAI
from langchain.tools import tool
from ddgs import DDGS
import warnings

from data_models import HealthcareProviderBasic
from utils import fetch_all_sync, fetch_all_npis_sync,_llm_parse
from config.urls import PROVIDERS, NPPES_URL


load_dotenv()
log.basicConfig(level=log.INFO)
warnings.filterwarnings("ignore", category=ResourceWarning)


@tool
def scrape_websites(provider_name: str) -> str:
    """
    Scrape all website pages for a healthcare provider.
    
    ALWAYS call this tool first before any other tool.
    
    INPUT:
        provider_name: exact name of the healthcare provider (e.g. 'Soin Medical Center')
    
    OUTPUT:
        Raw text content extracted from the provider's website including:
        - Provider details (address, phone, hours, website)
        - Practitioner names, specialties and other relevant information
        - Services offered, Accepted Insurances, ratings, Affliations
        Returns empty string if website is unreachable (404/timeout) — 
        if empty, fall back to search_web_llm.

    """
    log.info(f"[scrape] fetching pages for '{provider_name}'")
    try:
       result = fetch_all_sync(PROVIDERS[provider_name], provider_name)
       return result
    except Exception as e:
        log.warning(f"[scrape] fetching pages for '{provider_name}' failed: {e}")
        return ""
    

@tool
def search_web_llm(provider_name: str) -> str:
    """
    LLM-powered web search for a healthcare provider.
    Use as last resort fallback when scrape_websites returns empty.

    INPUT:
        provider_name: exact provider name (e.g. 'Soin Medical Center')

    OUTPUT:
        Relevant content only — address, phone, hours, website,
        practitioners, accepted insurance, affiliations, ratings.
        Returns empty string if search fails.
    """
    log.warning(f"[search_llm] falling back to LLM web search for '{provider_name}'")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    try:
        response = client.responses.create(
            model="gpt-5",
            reasoning={"effort": "medium"},
            tools=[{"type": "web_search"}],
            input=(
                f""" Find information about healthcare provider '{provider_name}'. 
                     Fetch relevant content only — skip unrelated content. 
                     Include: address, phone, hours, website,
                     practitioners (first name, last name, state, availability, qualification, certification), 
                     accepted insurance, hospital or network affiliations, Patient rating or review summaries."""
            ),
        )
        log.info(f"[search_llm] retrieved {len(response.output_text)} chars for '{provider_name}'")
        return response.output_text
    except Exception as e:
        log.warning(f"[search_llm] failed for '{provider_name}': {e}")
        return ""
    
@tool
def search_web_ddgs(provider_name: str, max_results: int = 5) -> str:
    """
    DuckDuckGo search for a healthcare provider's to supplements website data with external ratings, reviews, and insurance info
    that provider websites typically do not list themselves but not together with llm_search
    

    INPUT:
        provider_name: exact provider name (e.g. 'Soin Medical Center')

    OUTPUT:
        Relevant snippets covering ratings, reviews, insurance, affiliations.
        Returns empty string if search fails.
    """

    log.info(f"[search_ddgs] searching DuckDuckGo for '{provider_name}'")
    query = f"{provider_name} accepted insurance, hospital or network affiliations, Patient rating or review summaries"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return "\n\n".join(
            f"SOURCE: {r.get('href', '')}\n{r.get('body', '')}"
            for r in results
        )
    except Exception as e:
        log.warning(f"[search_ddgs] failed for '{provider_name}': {e}")
        return ""

@tool
def get_npi_data(raw_content: str) -> str:
    """
    Extract practitioner names from raw content and look up NPI numbers via NPPES API.

    INPUT:
        raw_content: complete raw text from all previous tool calls combined — do NOT summarize.

    OUTPUT:
        JSON mapping practitioner full name to their NPPES record including
        NPI number, credentials, taxonomies, and address.
        Returns empty JSON {} if no practitioners found or lookup fails.
    """
    log.info(f"[nppes] starting NPI lookup | content length: {len(raw_content)} chars")
    try:
        basic = _llm_parse(
            system=(
                f"""You are a Healthcare Provider Information extraction expert. Only extract what is explicitly present — never invent data"""
            ),
            user=f"""Extract first name, last name, and state for every practitioner mentioned.
                    State must be a two-letter code (e.g. OH).
                    If state is not mentioned, use the provider's location state.
                    Only extract what is explicitly present — never invent names based on the content provided 
                    {raw_content}""",
            output_format=HealthcareProviderBasic,
        )
        if not basic or not basic.practitioners:
            log.info("[nppes] no practitioners found — skipping")
            return json.dumps({})
        
        log.info(f"[nppes] found {len(basic.practitioners)} practitioners — querying NPPES")
        results = fetch_all_npis_sync(NPPES_URL, basic.practitioners)
        matched = sum(1 for v in results.values() if v)
        log.info(f"[nppes] matched {matched}/{len(results)} practitioners")
        return json.dumps(results, indent=2)
    except Exception as e:
        log.warning(f"[nppes] failed: {e}")
        return json.dumps({})

