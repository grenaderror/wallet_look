from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from wallet_look.detector import detect_chain
from wallet_look.models import Portfolio
from wallet_look.pricing import PricingClient

WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"

STABLECOIN_SYMBOLS = {
    "USDC",
    "USDT",
    "DAI",
    "USDE",
    "FDUSD",
    "TUSD",
    "BUSD",
    "PYUSD",
    "FRAX",
    "USDD",
}

SOLANA_STABLE_MINTS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
}


@dataclass
class InferredCostBasis:
    symbol: str
    avg_price: float
    total_bought: float
    total_spent_usd: float
    tx_count: int
    chain: str
    contract_address: Optional[str] = None
    sample_tx: Optional[str] = None


def parse_cost_basis_arg(arg: str) -> Dict[str, float]:
    """Parse a cost basis string formatted like 'ETH:2500,SOL:140' or 'btc=65,000.50 eth:$3,200'."""
    if not arg or not arg.strip():
        return {}

    cost_map: Dict[str, float] = {}
    matches = re.findall(r"([A-Za-z0-9_\-\.]+)\s*[:=]\s*([0-9$,.]+)", arg.strip())
    for sym, val in matches:
        sym_clean = sym.strip().upper()
        clean_val = val.strip().replace("$", "").replace(",", "")
        try:
            price_val = float(clean_val)
            if price_val > 0:
                cost_map[sym_clean] = price_val
        except (ValueError, TypeError):
            continue

    return cost_map


def apply_cost_basis(portfolios: List[Portfolio], cost_map: Dict[str, float]) -> None:
    """Apply cost basis entries to matching holdings in portfolios."""
    if not cost_map:
        return

    # Normalize lookup map to uppercase
    normalized_map = {k.upper(): v for k, v in cost_map.items()}

    for p in portfolios:
        for h in p.holdings:
            sym = h.symbol.upper()
            base_sym = sym.split("-")[0].strip()
            contract = (h.contract_address or "").strip().upper()
            contract_short_4 = f"{contract[:4]}...{contract[-4:]}" if len(contract) > 10 else ""
            contract_short_6 = f"{contract[:6]}...{contract[-4:]}" if len(contract) > 12 else ""

            target_cost = None
            if sym in normalized_map:
                target_cost = normalized_map[sym]
            elif base_sym in normalized_map:
                target_cost = normalized_map[base_sym]
            elif contract and contract in normalized_map:
                target_cost = normalized_map[contract]
            elif contract_short_4 and contract_short_4 in normalized_map:
                target_cost = normalized_map[contract_short_4]
            elif contract_short_6 and contract_short_6 in normalized_map:
                target_cost = normalized_map[contract_short_6]

            if target_cost is not None and target_cost > 0:
                h.cost_basis = target_cost
                h.cost_total_usd = round(h.balance * target_cost, 6)
                if h.value_usd is not None:
                    h.pnl_usd = round(h.value_usd - h.cost_total_usd, 6)
                if h.price_usd is not None:
                    h.pnl_pct = round(((h.price_usd - target_cost) / target_cost) * 100, 2)


def infer_from_hyperliquid(address: str, timeout: float = 10.0) -> Dict[str, InferredCostBasis]:
    """Infer cost basis for Hyperliquid spot & perps fills via userFills."""
    results: Dict[str, InferredCostBasis] = {}
    clean_addr = address.strip().lower()
    url = "https://api.hyperliquid.xyz/info"

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                url,
                json={"type": "userFills", "user": clean_addr},
                headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
            )
            if resp.status_code != 200:
                return {}
            fills = resp.json()
            if not isinstance(fills, list):
                return {}

            grouped: Dict[str, Dict[str, Any]] = {}
            for f in fills:
                if f.get("side") != "B":  # Only look at Buy orders
                    continue
                coin = str(f.get("coin", "")).upper()
                if not coin:
                    continue

                try:
                    px = float(f.get("px", 0.0))
                    sz = float(f.get("sz", 0.0))
                except (ValueError, TypeError):
                    continue

                if px <= 0 or sz <= 0:
                    continue

                if coin not in grouped:
                    grouped[coin] = {
                        "total_spent": 0.0,
                        "total_sz": 0.0,
                        "count": 0,
                        "sample_hash": str(f.get("oid") or ""),
                    }
                grouped[coin]["total_spent"] += px * sz
                grouped[coin]["total_sz"] += sz
                grouped[coin]["count"] += 1

            for coin, data in grouped.items():
                if data["total_sz"] > 0:
                    avg_px = data["total_spent"] / data["total_sz"]
                    results[coin] = InferredCostBasis(
                        symbol=coin,
                        avg_price=round(avg_px, 6),
                        total_bought=round(data["total_sz"], 4),
                        total_spent_usd=round(data["total_spent"], 2),
                        tx_count=data["count"],
                        chain="hyperliquid",
                        sample_tx=data["sample_hash"],
                    )
    except Exception:
        pass

    return results


def infer_from_evm(address: str, timeout: float = 12.0) -> Dict[str, InferredCostBasis]:
    """Infer cost basis from EVM token transfer history via Ethplorer."""
    results: Dict[str, InferredCostBasis] = {}
    clean_addr = address.strip().lower()
    url = f"https://api.ethplorer.io/getAddressHistory/{clean_addr}?apiKey=freekey&type=transfer&limit=50"

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
            if resp.status_code != 200:
                return {}
            data = resp.json()
            ops = data.get("operations", [])
            if not isinstance(ops, list):
                return {}

            # Group transfers by transactionHash
            tx_groups: Dict[str, List[dict]] = {}
            for op in ops:
                tx_hash = op.get("transactionHash")
                if tx_hash:
                    tx_groups.setdefault(tx_hash, []).append(op)

            grouped: Dict[str, Dict[str, Any]] = {}
            for tx_hash, group in tx_groups.items():
                # Find outgoing stablecoin transfers
                stable_spends: List[dict] = []
                token_receives: List[dict] = []

                for op in group:
                    tinfo = op.get("tokenInfo") or {}
                    sym = (tinfo.get("symbol") or "").upper()
                    from_addr = (op.get("from") or "").lower()
                    to_addr = (op.get("to") or "").lower()

                    if from_addr == clean_addr and sym in STABLECOIN_SYMBOLS:
                        stable_spends.append(op)
                    elif to_addr == clean_addr and sym not in STABLECOIN_SYMBOLS and sym:
                        token_receives.append(op)

                # If this tx has stablecoin spent AND token received -> DEX swap!
                if stable_spends and token_receives:
                    total_spent_usd = 0.0
                    for s in stable_spends:
                        dec = int(s.get("tokenInfo", {}).get("decimals") or 6)
                        try:
                            total_spent_usd += int(s.get("value", 0)) / (10**dec)
                        except (ValueError, TypeError):
                            pass

                    if total_spent_usd <= 0:
                        continue

                    # If multiple received tokens, divide cost proportionally or attribute to primary
                    for t in token_receives:
                        tsym = (t.get("tokenInfo", {}).get("symbol") or "UNKNOWN").upper()
                        tdec = int(t.get("tokenInfo", {}).get("decimals") or 18)
                        try:
                            bought_amt = int(t.get("value", 0)) / (10**tdec)
                        except (ValueError, TypeError):
                            bought_amt = 0.0

                        if bought_amt <= 0:
                            continue

                        if tsym not in grouped:
                            grouped[tsym] = {
                                "total_spent": 0.0,
                                "total_bought": 0.0,
                                "count": 0,
                                "contract_address": t.get("tokenInfo", {}).get("address"),
                                "sample_hash": tx_hash,
                            }
                        grouped[tsym]["total_spent"] += total_spent_usd / len(token_receives)
                        grouped[tsym]["total_bought"] += bought_amt
                        grouped[tsym]["count"] += 1

            for sym, g in grouped.items():
                if g["total_bought"] > 0:
                    avg_px = g["total_spent"] / g["total_bought"]
                    results[sym] = InferredCostBasis(
                        symbol=sym,
                        avg_price=round(avg_px, 6),
                        total_bought=round(g["total_bought"], 4),
                        total_spent_usd=round(g["total_spent"], 2),
                        tx_count=g["count"],
                        chain="ethereum",
                        contract_address=g.get("contract_address"),
                        sample_tx=g["sample_hash"],
                    )
    except Exception:
        pass

    return results


def infer_from_solana(address: str, timeout: float = 12.0) -> Dict[str, InferredCostBasis]:
    """Infer cost basis from Solana transactions where stablecoin balances decreased and tokens increased."""
    results: Dict[str, InferredCostBasis] = {}
    clean_addr = address.strip()
    rpc_urls = ["https://api.mainnet-beta.solana.com", "https://solana-rpc.publicnode.com"]

    try:
        with httpx.Client(timeout=timeout) as client:
            # 1. Fetch recent transaction signatures
            sigs: List[str] = []
            for rpc in rpc_urls:
                try:
                    payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getSignaturesForAddress",
                        "params": [clean_addr, {"limit": 15}],
                    }
                    r = client.post(rpc, json=payload, headers={"User-Agent": "wallet-look/0.1"})
                    if r.status_code == 200:
                        data = r.json().get("result")
                        if isinstance(data, list):
                            sigs = [item["signature"] for item in data if "signature" in item]
                            break
                except Exception:
                    continue

            if not sigs:
                return {}

            grouped: Dict[str, Dict[str, Any]] = {}

            # 2. Inspect transactions
            for sig in sigs[:10]:
                for rpc in rpc_urls:
                    try:
                        tx_payload = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "getTransaction",
                            "params": [
                                sig,
                                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
                            ],
                        }
                        r = client.post(rpc, json=tx_payload, headers={"User-Agent": "wallet-look/0.1"})
                        if r.status_code != 200:
                            continue
                        tx_data = r.json().get("result")
                        if not tx_data:
                            continue

                        meta = tx_data.get("meta", {})
                        pre_token = meta.get("preTokenBalances", [])
                        post_token = meta.get("postTokenBalances", [])

                        # Calculate balance delta for target owner
                        deltas: Dict[str, float] = {}
                        for post in post_token:
                            if post.get("owner") == clean_addr:
                                mint = post.get("mint", "")
                                amt = float(post.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
                                deltas[mint] = amt

                        for pre in pre_token:
                            if pre.get("owner") == clean_addr:
                                mint = pre.get("mint", "")
                                amt = float(pre.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
                                if mint in deltas:
                                    deltas[mint] -= amt
                                else:
                                    deltas[mint] = -amt

                        # Check if stablecoin decreased (spent) and other token increased (bought)
                        stable_spent = 0.0
                        for mint, delta in list(deltas.items()):
                            if mint in SOLANA_STABLE_MINTS and delta < 0:
                                stable_spent += abs(delta)

                        if stable_spent > 0:
                            for mint, delta in deltas.items():
                                if mint not in SOLANA_STABLE_MINTS and delta > 0:
                                    if mint not in grouped:
                                        grouped[mint] = {
                                            "total_spent": 0.0,
                                            "total_bought": 0.0,
                                            "count": 0,
                                            "sample_hash": sig,
                                        }
                                    grouped[mint]["total_spent"] += stable_spent
                                    grouped[mint]["total_bought"] += delta
                                    grouped[mint]["count"] += 1

                            # Check if native SOL increased
                            account_keys = (
                                tx_data.get("transaction", {}).get("message", {}).get("accountKeys", [])
                            )
                            user_idx = None
                            for idx, ak in enumerate(account_keys):
                                pubkey = ak.get("pubkey") if isinstance(ak, dict) else ak
                                if pubkey == clean_addr:
                                    user_idx = idx
                                    break

                            if user_idx is not None:
                                pre_bal = meta.get("preBalances", [])
                                post_bal = meta.get("postBalances", [])
                                if len(pre_bal) > user_idx and len(post_bal) > user_idx:
                                    lamport_diff = post_bal[user_idx] - pre_bal[user_idx]
                                    if lamport_diff > 1_000_000:  # > 0.001 SOL
                                        sol_bought = lamport_diff / 1e9
                                        if WRAPPED_SOL_MINT not in grouped:
                                            grouped[WRAPPED_SOL_MINT] = {
                                                "total_spent": 0.0,
                                                "total_bought": 0.0,
                                                "count": 0,
                                                "sample_hash": sig,
                                            }
                                        grouped[WRAPPED_SOL_MINT]["total_spent"] += stable_spent
                                        grouped[WRAPPED_SOL_MINT]["total_bought"] += sol_bought
                                        grouped[WRAPPED_SOL_MINT]["count"] += 1
                        break
                    except Exception:
                        continue

            pricing = PricingClient(timeout=timeout)
            mints_to_resolve = [m for m in grouped.keys() if m != WRAPPED_SOL_MINT]
            prices_map = pricing.get_prices("solana", mints_to_resolve) if mints_to_resolve else {}

            for mint, g in grouped.items():
                if g["total_bought"] > 0:
                    avg_px = g["total_spent"] / g["total_bought"]
                    if mint == WRAPPED_SOL_MINT:
                        sym = "SOL"
                    elif mint in prices_map and prices_map[mint].get("symbol"):
                        sym = str(prices_map[mint]["symbol"]).upper()
                    else:
                        sym = f"{mint[:4]}...{mint[-4:]}"

                    results[sym] = InferredCostBasis(
                        symbol=sym,
                        avg_price=round(avg_px, 6),
                        total_bought=round(g["total_bought"], 4),
                        total_spent_usd=round(g["total_spent"], 2),
                        tx_count=g["count"],
                        chain="solana",
                        contract_address=mint,
                        sample_tx=g["sample_hash"],
                    )
    except Exception:
        pass

    return results


def infer_cost_basis_all(addresses: List[str], timeout: float = 12.0) -> Dict[str, InferredCostBasis]:
    """Scan all provided addresses across supported networks for stablecoin transactions."""
    merged: Dict[str, InferredCostBasis] = {}

    for addr in addresses:
        chain = detect_chain(addr)
        if chain in ("ethereum", "arbitrum", "base", "optimism", "polygon", "bsc", "avalanche", "hyperliquid", "hyperevm"):
            # 1. Check Hyperliquid order-book fills
            hl_res = infer_from_hyperliquid(addr, timeout=timeout)
            for k, v in hl_res.items():
                merged[k] = v

            # 2. Check EVM transfer logs
            evm_res = infer_from_evm(addr, timeout=timeout)
            for k, v in evm_res.items():
                if k not in merged:
                    merged[k] = v

        elif chain == "solana":
            sol_res = infer_from_solana(addr, timeout=timeout)
            for k, v in sol_res.items():
                merged[k] = v

    return merged
