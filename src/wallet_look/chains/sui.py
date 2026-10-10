from __future__ import annotations

from typing import Dict, List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient

KNOWN_SUI_COINS: Dict[str, Dict[str, str | int]] = {
    "0x2::sui::SUI": {"symbol": "SUI", "name": "Sui", "decimals": 9},
    "0x0000000000000000000000000000000000000000000000000000000000000002::sui::SUI": {"symbol": "SUI", "name": "Sui", "decimals": 9},
    "0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
    "0x5d4b302506645c37ff133b98c4b50a5ae14841659738d6d733d59d0d257a93ab::weth::WETH": {"symbol": "WETH", "name": "Wrapped Ether", "decimals": 8},
    "0x5d4b302506645c37ff133b98c4b50a5ae14841659738d6d733d59d0d257a93ab::wbtc::WBTC": {"symbol": "WBTC", "name": "Wrapped Bitcoin", "decimals": 8},
    "0x5d4b302506645c37ff133b98c4b50a5ae14841659738d6d733d59d0d257a93ab::wusdc::WUSDC": {"symbol": "wUSDC", "name": "Wormhole USDC", "decimals": 6},
    "0x5d4b302506645c37ff133b98c4b50a5ae14841659738d6d733d59d0d257a93ab::wusdt::WUSDT": {"symbol": "wUSDT", "name": "Wormhole USDT", "decimals": 6},
    "0xc060006111016b8a020ad5b33834984a437aaa7d3c74c18e09a95d48aceab08c::coin::COIN": {"symbol": "USDT", "name": "Tether USD", "decimals": 6},
    "0x06834a3882517172d338b7b9b029f7f311635f037ecd3001ec9a0f7044a9d8a6::cetus::CETUS": {"symbol": "CETUS", "name": "Cetus Token", "decimals": 9},
    "0xa99b8952d439be02263b64fa6d414e8a600a9d8d5e9386ec6446f63076f4d1c::navx::NAVX": {"symbol": "NAVX", "name": "NAVI Protocol", "decimals": 9},
    "0x701633f7474f7ade3bcb03201d3fb3766a4436888845e8b355530239b563387::deep::DEEP": {"symbol": "DEEP", "name": "DeepBook Token", "decimals": 6},
}

GRAPHQL_QUERY = """
query getBalances($owner: SuiAddress!) {
  address(address: $owner) {
    balances {
      nodes {
        coinType {
          repr
        }
        totalBalance
      }
    }
  }
}
"""


class SuiFetcher(BaseChainFetcher):
    """Fetcher for Sui addresses via Sui GraphQL mainnet API."""

    GRAPHQL_URL = "https://graphql.mainnet.sui.io/graphql"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain="sui")

        balances_nodes = self._fetch_balances(clean_addr)
        if not balances_nodes:
            return portfolio

        # 1. Parse coin entries
        raw_coins: Dict[str, int] = {}
        for node in balances_nodes:
            if not isinstance(node, dict):
                continue
            coin_type_obj = node.get("coinType") or {}
            repr_str = coin_type_obj.get("repr")
            total_bal = node.get("totalBalance")
            if repr_str and total_bal is not None:
                try:
                    raw_coins[repr_str] = int(total_bal)
                except (ValueError, TypeError):
                    pass

        if not raw_coins:
            return portfolio

        # 2. Query DefiLlama for prices
        # Query coin representations with sui: prefix, and coingecko:sui for native
        llama_query_keys = ["coingecko:sui"] + [f"sui:{c}" for c in raw_coins.keys()]
        llama_prices = self.pricing._fetch_defillama("sui", llama_query_keys)

        # 3. Build holdings
        for coin_repr, raw_bal in raw_coins.items():
            is_native = coin_repr.endswith("::sui::SUI") or coin_repr in (
                "0x2::sui::SUI",
                "0x0000000000000000000000000000000000000000000000000000000000000002::sui::SUI",
            )

            known = KNOWN_SUI_COINS.get(coin_repr, {})
            price_info = (
                llama_prices.get(f"sui:{coin_repr}")
                or llama_prices.get(coin_repr)
                or (llama_prices.get("coingecko:sui") if is_native else None)
                or {}
            )

            if is_native:
                decimals = 9
                symbol = "SUI"
                name = "Sui"
                contract_address = None
            else:
                decimals_val = price_info.get("decimals") or known.get("decimals") or 9
                try:
                    decimals = int(decimals_val)
                except (ValueError, TypeError):
                    decimals = 9

                parts = coin_repr.split("::")
                fallback_sym = parts[-1] if len(parts) >= 3 else coin_repr[:6]
                symbol = str(price_info.get("symbol") or known.get("symbol") or fallback_sym)
                name = str(known.get("name") or price_info.get("name") or symbol)
                contract_address = coin_repr

            token_balance = raw_bal / (10 ** decimals)
            price_usd = float(price_info["price"]) if price_info.get("price") is not None else None

            portfolio.holdings.append(
                Holding(
                    symbol=symbol,
                    name=name,
                    balance=token_balance,
                    decimals=decimals,
                    contract_address=contract_address,
                    price_usd=price_usd,
                    is_native=is_native,
                    chain="sui",
                )
            )

        return portfolio

    def _fetch_balances(self, address: str) -> List[dict]:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    self.GRAPHQL_URL,
                    json={"query": GRAPHQL_QUERY, "variables": {"owner": address}},
                    headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    addr_data = data.get("data", {}).get("address")
                    if addr_data:
                        balances = addr_data.get("balances", {})
                        nodes = balances.get("nodes", [])
                        if isinstance(nodes, list):
                            return nodes
        except Exception:
            pass
        return []
