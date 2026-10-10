import pytest
from wallet_look.detector import detect_chain, is_btc_address, is_eth_address, is_sol_address
from wallet_look.models import ChainType


def test_is_eth_address():
    valid = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert is_eth_address(valid) is True
    assert is_eth_address(valid.lower()) is True
    assert is_eth_address(valid.upper().replace("0X", "0x")) is True

    # Invalid lengths or characters
    assert is_eth_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA9604") is False  # 41 chars
    assert is_eth_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA9604555") is False  # 44 chars
    assert is_eth_address("d8dA6BF26964aF9D7eEd9e03E53415D37aA96045") is False  # missing 0x
    assert is_eth_address("0xG8dA6BF26964aF9D7eEd9e03E53415D37aA96045") is False  # 'G' invalid hex


def test_is_sol_address():
    valid = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    assert is_sol_address(valid) is True
    assert is_sol_address("So11111111111111111111111111111111111111112") is True

    # Invalid Base58 characters (0, O, I, l are disallowed in Base58)
    assert is_sol_address("0WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM") is False
    assert is_sol_address("OWzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM") is False
    assert is_sol_address("short") is False


def test_is_btc_address():
    assert is_btc_address("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") is True  # P2PKH
    assert is_btc_address("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy") is True  # P2SH
    assert is_btc_address("bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq") is True  # Bech32
    assert is_btc_address("invalid_address") is False


def test_detect_chain():
    assert detect_chain("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045") == ChainType.ETHEREUM
    assert detect_chain(" 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 ") == ChainType.ETHEREUM
    assert detect_chain("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM") == ChainType.SOLANA
    assert detect_chain("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa") == ChainType.BITCOIN

    with pytest.raises(ValueError, match="Unable to auto-detect blockchain"):
        detect_chain("not_a_crypto_address")
