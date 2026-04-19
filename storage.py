# storage.py
# Saves and loads extracted provider data to/from a local JSON file.
# Simple file-based cache — no database needed.
# Each provider is stored by its key from config/urls.py.

import json
import os
from data_models import HealthcareProvider
import logging as log
from datetime import datetime

log.basicConfig(level=log.INFO)

STORAGE_FILE = "storage/providers.json"

def _load_raw() -> dict:
    """Load the full JSON file. Returns empty dict if file doesn't exist."""
    if not os.path.exists(STORAGE_FILE):
        return {}
    with open(STORAGE_FILE) as f:
        return json.load(f)
    
def save_provider(provider_name: str, provider: HealthcareProvider) -> None:
    """Save one provider to the JSON store."""
    data = _load_raw()
    data[provider_name] = json.loads(provider.model_dump_json())
    os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)
    log.info(f"[storage] saved '{provider_name}'")


def load_provider(provider_name: str) -> HealthcareProvider | None:
    """
    Load a provider from the JSON store.
    Returns None if not found —  should run extraction instead.
    """
    data = _load_raw()
    if provider_name not in data:
        log.info(f"[storage] '{provider_name}' not in store — needs extraction")
        return None
    log.info(f"[storage] loaded '{provider_name}' from cache")
    return HealthcareProvider.model_validate(data[provider_name])


def exists(provider_name: str) -> bool:
    """Check if a provider is already stored."""
    return provider_name in _load_raw()



