import pytest
from wallet_look.cross_chain import (
    b58decode,
    b58encode,
    derive_eth_from_sol,
    derive_sol_from_eth,
    get_equivalent_chain_and_address,
    to_checksum_address,
)
from wallet_look.models import ChainType


def test_base58_roundtrip():
    data = b"\x00\x00\x01\x02\x03hello\xff\xee"
    encoded = b58encode(data)
    decoded = b58decode(encoded)
    assert decoded == data


def test_base58_invalid_character():
    with pytest.raises(ValueError, match="Invalid Base58 character"):
        b58decode("0OIl")  # Disallowed characters in Base58


def test_checksum_address():
    raw_addr = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    expected = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert to_checksum_address(raw_addr) == expected


def test_derive_eth_from_sol_left_padded():
    # An encoded 20-byte EVM address with 12 leading zeros
    original_eth = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    raw_bytes = b"\x00" * 12 + bytes.fromhex(original_eth[2:])
    sol_addr = b58encode(raw_bytes)

    derived_eth, method = derive_eth_from_sol(sol_addr)
    assert derived_eth.lower() == original_eth.lower()
    assert "Left-Padded" in method


def test_derive_eth_from_sol_neon():
    sol_addr = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    derived_eth, method = derive_eth_from_sol(sol_addr)

    assert derived_eth.startswith("0x")
    assert len(derived_eth) == 42
    assert "Neon EVM" in method


def test_derive_sol_from_eth(monkeypatch):
    eth_addr = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

    # 1. Fallback to 32-byte left-padded representation when ENS has no SOL record
    monkeypatch.setattr("wallet_look.cross_chain.get_ens_sol_wallet", lambda addr: None)
    derived_sol, method = derive_sol_from_eth(eth_addr)
    assert len(derived_sol) >= 32
    assert "SVM Foreign Representation" in method

    # 2. When ENS has configured SOL wallet
    monkeypatch.setattr(
        "wallet_look.cross_chain.get_ens_sol_wallet",
        lambda addr: ("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", "ENS Record (vitalik.eth)"),
    )
    ens_sol, method_ens = derive_sol_from_eth(eth_addr)
    assert ens_sol == "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    assert "ENS Record" in method_ens


def test_get_equivalent_chain_and_address():
    # Solana -> Ethereum
    res_sol = get_equivalent_chain_and_address(
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", ChainType.SOLANA
    )
    assert res_sol is not None
    eq_addr, eq_chain, method = res_sol
    assert eq_chain == ChainType.ETHEREUM
    assert eq_addr.startswith("0x")

    # Ethereum -> Solana
    res_eth = get_equivalent_chain_and_address(
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", ChainType.ETHEREUM
    )
    assert res_eth is not None
    eq_addr, eq_chain, method = res_eth
    assert eq_chain == ChainType.SOLANA

    # Bitcoin has no cross-chain equivalent
    assert (
        get_equivalent_chain_and_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", ChainType.BITCOIN)
        is None
    )
