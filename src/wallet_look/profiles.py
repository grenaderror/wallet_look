from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

CONFIG_DIR = Path.home() / ".config" / "wallet-look"
PROFILES_FILE = CONFIG_DIR / "profiles.json"


def _ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_raw_profiles() -> Dict[str, dict]:
    """Load all saved wallet profiles in normalized dictionary form."""
    if not PROFILES_FILE.exists():
        return {}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                normalized: Dict[str, dict] = {}
                for k, v in data.items():
                    if isinstance(v, list):
                        normalized[k] = {"addresses": v, "cost_basis": {}}
                    elif isinstance(v, dict):
                        normalized[k] = {
                            "addresses": v.get("addresses", []),
                            "cost_basis": v.get("cost_basis", {}),
                        }
                return normalized
    except Exception:
        pass
    return {}


def save_raw_profiles(raw: Dict[str, dict]) -> None:
    _ensure_config_dir()
    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)


def load_profiles() -> Dict[str, List[str]]:
    """Load all saved wallet profiles, returning profile name -> list of addresses."""
    raw = load_raw_profiles()
    return {k: v["addresses"] for k, v in raw.items()}


def save_profile(
    name: str,
    addresses: List[str],
    cost_basis: Optional[Dict[str, float]] = None,
) -> None:
    """Save a wallet profile with a list of addresses and optional cost basis."""
    _ensure_config_dir()
    raw = load_raw_profiles()
    clean_name = name.strip()
    deduped = list(dict.fromkeys(a.strip() for a in addresses if a.strip()))

    existing = raw.get(clean_name, {})
    existing_costs = existing.get("cost_basis", {})
    if cost_basis is not None:
        merged_costs = {**existing_costs, **{k.upper(): float(v) for k, v in cost_basis.items()}}
    else:
        merged_costs = existing_costs

    raw[clean_name] = {
        "addresses": deduped,
        "cost_basis": merged_costs,
    }
    save_raw_profiles(raw)


def get_profile(name: str) -> Optional[List[str]]:
    """Retrieve addresses for a named profile."""
    raw = load_raw_profiles()
    entry = raw.get(name.strip())
    return entry["addresses"] if entry else None


def get_profile_cost_basis(name: str) -> Dict[str, float]:
    """Retrieve cost basis dictionary for a named profile."""
    raw = load_raw_profiles()
    entry = raw.get(name.strip())
    return entry.get("cost_basis", {}) if entry else {}


def set_profile_cost_basis(name: str, cost_basis: Dict[str, float]) -> bool:
    """Set or update cost basis for a named profile."""
    raw = load_raw_profiles()
    clean_name = name.strip()
    if clean_name not in raw:
        return False
    current_costs = dict(raw[clean_name].get("cost_basis", {}))
    for k, v in cost_basis.items():
        current_costs[k.upper()] = float(v)
    raw[clean_name]["cost_basis"] = current_costs
    save_raw_profiles(raw)
    return True


def delete_profile(name: str) -> bool:
    """Delete a profile by name."""
    raw = load_raw_profiles()
    clean_name = name.strip()
    if clean_name in raw:
        del raw[clean_name]
        save_raw_profiles(raw)
        return True
    return False


def list_profiles() -> List[str]:
    """Return a list of all profile names."""
    return list(load_raw_profiles().keys())

