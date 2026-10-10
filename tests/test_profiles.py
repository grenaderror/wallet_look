import json
from wallet_look.profiles import (
    delete_profile,
    get_profile,
    get_profile_cost_basis,
    list_profiles,
    load_profiles,
    load_raw_profiles,
    save_profile,
    set_profile_cost_basis,
)


def test_profile_cost_basis_lifecycle(tmp_path, monkeypatch):
    test_file = tmp_path / "profiles.json"
    monkeypatch.setattr("wallet_look.profiles.PROFILES_FILE", test_file)

    # 1. Save profile with addresses and cost basis
    save_profile("vault", ["0x123", "0x456"], cost_basis={"ETH": 2500.0, "SOL": 140.0})

    assert get_profile("vault") == ["0x123", "0x456"]
    assert get_profile_cost_basis("vault") == {"ETH": 2500.0, "SOL": 140.0}

    # 2. Update cost basis
    set_profile_cost_basis("vault", {"ETH": 2600.0, "BTC": 65000.0})
    costs = get_profile_cost_basis("vault")
    assert costs["ETH"] == 2600.0
    assert costs["SOL"] == 140.0
    assert costs["BTC"] == 65000.0

    # 3. List profiles
    assert "vault" in list_profiles()

    # 4. Delete profile
    assert delete_profile("vault") is True
    assert get_profile("vault") is None
    assert get_profile_cost_basis("vault") == {}


def test_legacy_profile_backward_compatibility(tmp_path, monkeypatch):
    test_file = tmp_path / "profiles.json"
    monkeypatch.setattr("wallet_look.profiles.PROFILES_FILE", test_file)

    # Legacy format is {"mywallet": ["0xabc", "0xdef"]}
    legacy_data = {"legacy_wallet": ["0xabc", "0xdef"]}
    test_file.write_text(json.dumps(legacy_data), encoding="utf-8")

    assert get_profile("legacy_wallet") == ["0xabc", "0xdef"]
    assert get_profile_cost_basis("legacy_wallet") == {}
    assert load_profiles() == {"legacy_wallet": ["0xabc", "0xdef"]}

    # Setting cost basis should seamlessly upgrade the entry
    set_profile_cost_basis("legacy_wallet", {"ETH": 3000.0})
    assert get_profile("legacy_wallet") == ["0xabc", "0xdef"]
    assert get_profile_cost_basis("legacy_wallet") == {"ETH": 3000.0}
