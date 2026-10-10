import re
from wallet_look.models import ChainType

BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
HEX_ALPHABET = set("0123456789abcdefABCDEF")


def is_eth_address(address: str) -> bool:
    """Check if address is a valid Ethereum / EVM address."""
    if not address.startswith("0x") or len(address) != 42:
        return False
    return all(c in HEX_ALPHABET for c in address[2:])


def is_sol_address(address: str) -> bool:
    """Check if address is a valid Solana public key (base58, 32-44 characters)."""
    if len(address) < 32 or len(address) > 44:
        return False
    # Avoid matching pure hex strings or 0x strings
    if address.startswith("0x"):
        return False
    # Solana base58 shouldn't be confused with Bitcoin if it's 43-44 characters
    return all(c in BASE58_ALPHABET for c in address)


def is_btc_address(address: str) -> bool:
    """Check if address is a valid Bitcoin address (P2PKH, P2SH, or Bech32)."""
    clean = address.strip()
    # Bech32 Segwit / Taproot: starts with bc1
    if clean.lower().startswith("bc1"):
        return bool(re.match(r"^bc1[a-z0-9]{11,71}$", clean.lower()))
    # Legacy P2PKH (starts with 1) or P2SH (starts with 3)
    if (clean.startswith("1") or clean.startswith("3")) and 26 <= len(clean) <= 35:
        return all(c in BASE58_ALPHABET for c in clean)
    return False


def detect_chain(address: str) -> ChainType:
    """
    Detect the blockchain for a given address.
    Supports Ethereum, Solana, and Bitcoin.
    """
    cleaned = address.strip()

    if is_eth_address(cleaned):
        return ChainType.ETHEREUM

    # Check Bitcoin before Solana for legacy addresses starting with 1 or 3
    if is_btc_address(cleaned):
        return ChainType.BITCOIN

    if is_sol_address(cleaned):
        return ChainType.SOLANA

    raise ValueError(
        f"Unable to auto-detect blockchain for address '{address}'. "
        "Supported formats: ETH (0x...), SOL (Base58 32-44 chars), BTC (1..., 3..., bc1...)."
    )
