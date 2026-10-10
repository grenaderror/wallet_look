from __future__ import annotations

from typing import Optional, Tuple
import Crypto.Hash.keccak
import httpx

from wallet_look.models import ChainType

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(v: str) -> bytes:
    """Decode a Base58 string into raw bytes."""
    num = 0
    for char in v:
        idx = ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid Base58 character: '{char}'")
        num = num * 58 + idx
    combined = num.to_bytes((num.bit_length() + 7) // 8, "big") if num > 0 else b""
    pad = 0
    for c in v:
        if c == ALPHABET[0]:
            pad += 1
        else:
            break
    return b"\x00" * pad + combined


def b58encode(b: bytes) -> str:
    """Encode raw bytes into a Base58 string."""
    num = int.from_bytes(b, "big")
    res = []
    while num > 0:
        num, r = divmod(num, 58)
        res.append(ALPHABET[r])
    res_str = "".join(reversed(res))
    pad = 0
    for byte in b:
        if byte == 0:
            pad += 1
        else:
            break
    return "1" * pad + res_str


def to_checksum_address(address_hex: str) -> str:
    """Convert an Ethereum address hex string to EIP-55 checksum format."""
    clean = address_hex.lower().replace("0x", "")
    k = Crypto.Hash.keccak.new(digest_bits=256)
    k.update(clean.encode("utf-8"))
    hash_hex = k.hexdigest()
    res = ["0x"]
    for i, c in enumerate(clean):
        if c in "0123456789":
            res.append(c)
        else:
            res.append(c.upper() if int(hash_hex[i], 16) >= 8 else c)
    return "".join(res)


def get_ens_sol_wallet(eth_address: str, timeout: float = 3.0) -> Optional[Tuple[str, str]]:
    """Check if the given ETH address has an ENS name with a configured SOL wallet record."""
    url = f"https://api.ensdata.net/{eth_address.strip()}"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
            if resp.status_code == 200:
                data = resp.json()
                ens_name = data.get("ens") or data.get("ens_primary") or ""
                wallets = data.get("wallets", {})
                sol_wallet = wallets.get("sol")
                if sol_wallet:
                    return sol_wallet, f"ENS Record ({ens_name})" if ens_name else "ENS Record"
    except Exception:
        pass
    return None


def derive_eth_from_sol(sol_address: str) -> Tuple[str, str]:
    """
    Derive the equivalent Ethereum address from a Solana address:
    1. If the Solana address is a left-padded 32-byte representation (12 leading null bytes), unpack it directly.
    2. Otherwise, apply the standard SVM-to-EVM mapping (Neon EVM: Keccak-256 of public key).
    """
    raw_pubkey = b58decode(sol_address.strip())

    # Check for left-padded 20-byte EVM address (e.g. 12 leading zeros)
    if len(raw_pubkey) == 32 and raw_pubkey[:12] == b"\x00" * 12:
        eth_raw = raw_pubkey[12:].hex()
        return to_checksum_address("0x" + eth_raw), "Decoded EVM (Left-Padded)"

    # Standard SVM -> EVM mapping via Keccak-256
    k = Crypto.Hash.keccak.new(digest_bits=256)
    k.update(raw_pubkey)
    eth_raw = k.digest()[-20:].hex()
    return to_checksum_address("0x" + eth_raw), "Neon EVM (Keccak-256)"


def derive_sol_from_eth(eth_address: str) -> Tuple[str, str]:
    """
    Get the equivalent Solana address from an Ethereum address:
    1. First check if the Ethereum address has a configured SOL wallet on ENS.
    2. Otherwise derive the standard 32-byte SVM foreign address representation (left-padded with 12 zero bytes).
    """
    clean_eth = eth_address.strip()

    # 1. Check ENS record
    ens_sol = get_ens_sol_wallet(clean_eth)
    if ens_sol:
        return ens_sol

    # 2. Derive standard 32-byte foreign address representation
    raw_eth = bytes.fromhex(clean_eth.lower().replace("0x", ""))
    padded_32 = b"\x00" * 12 + raw_eth
    return b58encode(padded_32), "SVM Foreign Representation (Left-Padded 32-byte)"


def get_equivalent_chain_and_address(
    address: str, chain: ChainType
) -> Optional[Tuple[str, ChainType, str]]:
    """
    Given an address and its primary chain, return:
    (equivalent_address, target_chain, derivation_description)
    or None if not applicable.
    """
    if chain == ChainType.SOLANA:
        eq_addr, method = derive_eth_from_sol(address)
        return eq_addr, ChainType.ETHEREUM, method
    elif chain == ChainType.ETHEREUM:
        eq_addr, method = derive_sol_from_eth(address)
        return eq_addr, ChainType.SOLANA, method
    return None
