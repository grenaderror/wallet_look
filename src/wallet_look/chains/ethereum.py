from __future__ import annotations

from typing import List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient


class EthereumFetcher(BaseChainFetcher):
    """Fetcher for Ethereum mainnet native balance and ERC-20 tokens."""

    ETHPLORER_URL = "https://api.ethplorer.io/getAddressInfo/{address}?apiKey=freekey"
    PUBLIC_RPCS = [
        "https://eth.llamarpc.com",
        "https://cloudflare-eth.com",
    ]

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain="ethereum")

        # 1. Attempt Ethplorer to get native ETH and all ERC-20 tokens
        ethplorer_data = self._fetch_ethplorer(clean_addr)
        if ethplorer_data:
            holdings = self._parse_ethplorer_data(clean_addr, ethplorer_data)
            portfolio.holdings = holdings
            return portfolio

        # 2. Fallback: Query native balance via public RPC + DefiLlama pricing
        native_eth = self._fetch_native_via_rpc(clean_addr)
        if native_eth:
            portfolio.holdings.append(native_eth)

        return portfolio

    def _fetch_ethplorer(self, address: str) -> Optional[dict]:
        url = self.ETHPLORER_URL.format(address=address)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None

    def _parse_ethplorer_data(self, address: str, data: dict) -> List[Holding]:
        holdings: List[Holding] = []
        tokens_needing_price: List[str] = []

        # Native ETH
        eth_info = data.get("ETH", {})
        raw_eth_bal = eth_info.get("rawBalance")
        if raw_eth_bal is not None:
            eth_balance = int(raw_eth_bal) / 1e18
        else:
            eth_balance = float(eth_info.get("balance", 0.0))

        eth_price = None
        if isinstance(eth_info.get("price"), dict):
            rate = eth_info["price"].get("rate")
            if rate is not None:
                eth_price = float(rate)

        # ERC-20 Tokens
        tokens = data.get("tokens", [])
        for item in tokens:
            tinfo = item.get("tokenInfo", {})
            contract = tinfo.get("address", "")
            decimals_raw = tinfo.get("decimals", 18)
            try:
                decimals = int(decimals_raw)
            except (ValueError, TypeError):
                decimals = 18

            raw_bal = item.get("rawBalance")
            if raw_bal is not None:
                try:
                    balance = int(raw_bal) / (10**decimals)
                except (ValueError, TypeError):
                    balance = float(item.get("balance", 0.0))
            else:
                balance = float(item.get("balance", 0.0))

            symbol = tinfo.get("symbol") or "UNKNOWN"
            name = tinfo.get("name") or symbol

            token_price = None
            if isinstance(tinfo.get("price"), dict):
                rate = tinfo["price"].get("rate")
                if rate is not None:
                    token_price = float(rate)

            if token_price is None and contract and balance > 0:
                tokens_needing_price.append(contract)

            holdings.append(
                Holding(
                    symbol=symbol,
                    name=name,
                    balance=balance,
                    decimals=decimals,
                    contract_address=contract,
                    price_usd=token_price,
                    is_native=False,
                    chain="ethereum",
                )
            )

        # If ETH price is missing, request it too
        if eth_price is None:
            tokens_needing_price.append("0x0000000000000000000000000000000000000000")

        # Enrich missing prices via DefiLlama / DexScreener (limit to top 100 to stay fast)
        if tokens_needing_price:
            tokens_to_lookup = tokens_needing_price[:100]
            if "0x0000000000000000000000000000000000000000" not in tokens_to_lookup and eth_price is None:
                tokens_to_lookup.append("0x0000000000000000000000000000000000000000")
            prices_map = self.pricing.get_prices("ethereum", tokens_to_lookup)
            if "0x0000000000000000000000000000000000000000" in prices_map:
                p_eth = prices_map["0x0000000000000000000000000000000000000000"].get("price")
                if p_eth is not None:
                    eth_price = float(p_eth)

            for h in holdings:
                if h.price_usd is None and h.contract_address:
                    lookup = prices_map.get(h.contract_address.lower()) or prices_map.get(h.contract_address)
                    if lookup and lookup.get("price") is not None:
                        h.price_usd = float(lookup["price"])
                        h.value_usd = round(h.balance * h.price_usd, 6)

        # Prepend Native ETH
        holdings.insert(
            0,
            Holding(
                symbol="ETH",
                name="Ethereum",
                balance=eth_balance,
                decimals=18,
                contract_address=None,
                price_usd=eth_price,
                is_native=True,
                chain="ethereum",
            ),
        )

        return holdings

    def _fetch_native_via_rpc(self, address: str) -> Optional[Holding]:
        for rpc in self.PUBLIC_RPCS:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "eth_getBalance",
                    "params": [address, "latest"],
                }
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(rpc, json=payload, headers={"User-Agent": "wallet-look/0.1"})
                    if resp.status_code == 200:
                        res = resp.json().get("result")
                        if res:
                            balance = int(res, 16) / 1e18
                            # Get ETH price
                            prices = self.pricing.get_prices("ethereum", ["0x0000000000000000000000000000000000000000"])
                            eth_price_info = prices.get("0x0000000000000000000000000000000000000000", {})
                            eth_price = eth_price_info.get("price")
                            return Holding(
                                symbol="ETH",
                                name="Ethereum",
                                balance=balance,
                                decimals=18,
                                contract_address=None,
                                price_usd=float(eth_price) if eth_price is not None else None,
                                is_native=True,
                                chain="ethereum",
                            )
            except Exception:
                continue
        return None
