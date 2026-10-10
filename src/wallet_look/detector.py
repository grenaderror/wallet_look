import hashlib
import re
from wallet_look.models import ChainType

BASE58_STRING = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_ALPHABET = set(BASE58_STRING)
HEX_ALPHABET = set("0123456789abcdefABCDEF")


def is_eth_address(address: str) -> bool:
    """Check if address is a valid Ethereum / EVM address."""
    clean = address.strip()
    if not clean.startswith("0x") or len(clean) != 42:
        return False
    return all(c in HEX_ALPHABET for c in clean[2:])


def is_sui_address(address: str) -> bool:
    """Check if address is a valid Sui address (0x + 64 hex chars = 66 chars)."""
    clean = address.strip()
    if not clean.startswith("0x") or len(clean) != 66:
        return False
    return all(c in HEX_ALPHABET for c in clean[2:])


def is_tron_address(address: str) -> bool:
    """Check if address is a valid TRON address (Base58Check starting with T, 34 chars)."""
    clean = address.strip()
    if not clean.startswith("T") or len(clean) != 34:
        return False
    if not all(c in BASE58_ALPHABET for c in clean):
        return False
    try:
        val = 0
        for c in clean:
            val = val * 58 + BASE58_STRING.index(c)
        res = bytearray()
        while val > 0:
            val, mod = divmod(val, 256)
            res.append(mod)
        res.reverse()
        pad = len(clean) - len(clean.lstrip("1"))
        raw = b"\x00" * pad + bytes(res)
        if len(raw) != 25 or raw[0] != 0x41:
            return False
        chk = hashlib.sha256(hashlib.sha256(raw[:21]).digest()).digest()[:4]
        return raw[21:] == chk
    except Exception:
        return False


def is_sol_address(address: str) -> bool:
    """Check if address is a valid Solana public key (base58, 32-44 characters)."""
    clean = address.strip()
    if len(clean) < 32 or len(clean) > 44:
        return False
    # Avoid matching pure hex strings or 0x strings
    if clean.startswith("0x"):
        return False
    return all(c in BASE58_ALPHABET for c in clean)


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
    Supports Ethereum, Solana, Bitcoin, TRON, and SUI.
    """
    cleaned = address.strip()

    # Check SUI before ETH (66 chars vs 42 chars)
    if is_sui_address(cleaned):
        return ChainType.SUI

    if is_eth_address(cleaned):
        return ChainType.ETHEREUM

    # Check TRON before Solana
    if is_tron_address(cleaned):
        return ChainType.TRON

    # Check Bitcoin before Solana for legacy addresses starting with 1 or 3
    if is_btc_address(cleaned):
        return ChainType.BITCOIN

    if is_sol_address(cleaned):
        return ChainType.SOLANA

    raise ValueError(
        f"Unable to auto-detect blockchain for address '{address}'. "
        "Supported formats: ETH (0x...), SOL (Base58 32-44 chars), BTC (1..., 3..., bc1...), TRON (T... 34 chars), SUI (0x... 66 chars)."
    )
