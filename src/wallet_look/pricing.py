from __future__ import annotations

from typing import Dict, List, Optional
import httpx


class PricingClient:
    """Client for fetching live cryptocurrency prices from DefiLlama and DexScreener."""

    LLAMA_BASE = "https://coins.llama.fi/prices/current"
    DEXSCREENER_BASE = "https://api.dexscreener.com/latest/dex/tokens"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def get_prices(
        self,
        chain: str,
        token_addresses: List[str],
    ) -> Dict[str, Dict[str, Optional[float | str]]]:
        """
        Fetch prices for a list of token addresses on a given chain (e.g. 'ethereum', 'solana').
        Returns mapping: address -> {"price": float, "symbol": str, "name": str}
        """
        results: Dict[str, Dict[str, Optional[float | str]]] = {}
        if not token_addresses:
            return results

        # 1. First batch via DefiLlama
        llama_map = self._fetch_defillama(chain, token_addresses)
        results.update(llama_map)

        # 2. For tokens without price from DefiLlama, try DexScreener (at most 30 to stay fast)
        missing = [addr for addr in token_addresses if addr not in results or results[addr].get("price") is None][:30]
        if missing:
            dex_map = self._fetch_dexscreener(missing)
            for addr, info in dex_map.items():
                if addr in results:
                    if results[addr].get("price") is None and info.get("price") is not None:
                        results[addr]["price"] = info["price"]
                    if not results[addr].get("symbol") and info.get("symbol"):
                        results[addr]["symbol"] = info["symbol"]
                else:
                    results[addr] = info

        return results

    def _fetch_defillama(
        self,
        chain: str,
        token_addresses: List[str],
    ) -> Dict[str, Dict[str, Optional[float | str]]]:
        results: Dict[str, Dict[str, Optional[float | str]]] = {}
        chunk_size = 100

        # Map chain name to DefiLlama chain prefix
        chain_prefix = chain.lower()
        if chain_prefix == "eth":
            chain_prefix = "ethereum"
        elif chain_prefix == "sol":
            chain_prefix = "solana"
        elif chain_prefix == "btc":
            chain_prefix = "coingecko:bitcoin"

        for i in range(0, len(token_addresses), chunk_size):
            chunk = token_addresses[i : i + chunk_size]
            if chain_prefix == "coingecko:bitcoin":
                coins_param = "coingecko:bitcoin"
            else:
                coins_param = ",".join(f"{chain_prefix}:{addr}" for addr in chunk)

            url = f"{self.LLAMA_BASE}/{coins_param}"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
                    if resp.status_code == 200:
                        data = resp.json().get("coins", {})
                        for key, val in data.items():
                            raw_addr = key.split(":", 1)[1] if ":" in key else key
                            price = val.get("price")
                            symbol = val.get("symbol")
                            results[raw_addr] = {
                                "price": float(price) if price is not None else None,
                                "symbol": symbol,
                            }
            except Exception:
                # Continue gracefully on transient network errors
                pass

        return results

    def _fetch_dexscreener(
        self,
        token_addresses: List[str],
    ) -> Dict[str, Dict[str, Optional[float | str]]]:
        results: Dict[str, Dict[str, Optional[float | str]]] = {}
        chunk_size = 30

        for i in range(0, len(token_addresses), chunk_size):
            chunk = token_addresses[i : i + chunk_size]
            url = f"{self.DEXSCREENER_BASE}/{','.join(chunk)}"
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
                    if resp.status_code == 200:
                        data = resp.json()
                        pairs = data.get("pairs") or []
                        for pair in pairs:
                            base_token = pair.get("baseToken", {})
                            addr = base_token.get("address")
                            if not addr or addr in results:
                                continue
                            price_usd_str = pair.get("priceUsd")
                            price_usd = float(price_usd_str) if price_usd_str else None
                            results[addr] = {
                                "price": price_usd,
                                "symbol": base_token.get("symbol"),
                                "name": base_token.get("name"),
                            }
            except Exception:
                pass

        return results
