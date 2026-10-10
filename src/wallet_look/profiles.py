from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_DIR = Path.home() / ".config" / "wallet-look"
PROFILES_FILE = CONFIG_DIR / "profiles.json"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_profiles() -> Dict[str, List[str]]:
    """Load all saved wallet profiles."""
    if not PROFILES_FILE.exists():
        return {}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_profile(name: str, addresses: List[str]) -> None:
    """Save a wallet profile with a list of addresses."""
    _ensure_config_dir()
    profiles = load_profiles()
    # Deduplicate while preserving order
    deduped = list(dict.fromkeys(a.strip() for a in addresses if a.strip()))
    profiles[name.strip()] = deduped
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)


def get_profile(name: str) -> Optional[List[str]]:
    """Retrieve addresses for a named profile."""
    profiles = load_profiles()
    return profiles.get(name.strip())


def delete_profile(name: str) -> bool:
    """Delete a profile by name."""
    profiles = load_profiles()
    if name in profiles:
        del profiles[name]
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2)
        return True
    return False


def list_profiles() -> List[str]:
    """Return a list of all profile names."""
    return list(load_profiles().keys())

