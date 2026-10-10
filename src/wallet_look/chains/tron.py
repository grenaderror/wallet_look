from __future__ import annotations

from typing import Dict, List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient

KNOWN_TRC20: Dict[str, Dict[str, str | int]] = {
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": {"symbol": "USDT", "name": "Tether USD", "decimals": 6},
    "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8": {"symbol": "USDC", "name": "USD Coin", "decimals": 6},
    "TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn": {"symbol": "USDD", "name": "Decentralized USD", "decimals": 18},
    "TAFjULxiVgT4qWk6UZrutqufydgSQtKa37": {"symbol": "BTT", "name": "BitTorrent", "decimals": 18},
    "TCFLL5dxspstWocZBZaQEJHstZ3vnqn95n": {"symbol": "JST", "name": "JUST", "decimals": 18},
    "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S": {"symbol": "SUN", "name": "Sun Token", "decimals": 18},
    "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7": {"symbol": "WIN", "name": "WINKLink", "decimals": 6},
    "TFczXZPhnThNSqr5by8tvxsdC7KZRUMmg3": {"symbol": "NFT", "name": "APENFT", "decimals": 6},
    "TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9": {"symbol": "BTC", "name": "Bitcoin", "decimals": 8},
    "TXpw8XeWYeTUdGWBYAFRaQiKcF6aCXpqUC": {"symbol": "ETH", "name": "Ethereum", "decimals": 18},
}


class TronFetcher(BaseChainFetcher):
    """Fetcher for TRON addresses via TronGrid public API."""

    TRONGRID_URL = "https://api.trongrid.io/v1/accounts/{address}"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain="tron")

        account_data = self._fetch_account(clean_addr)
        if not account_data:
            # Address has no transactions or doesn't exist on-chain
            return portfolio

        # 1. Native TRX balance (in SUN: 1 TRX = 10^6 SUN)
        balance_sun = account_data.get("balance", 0)
        trx_balance = float(balance_sun) / 1e6

        # Fetch native TRX price from DefiLlama
        llama_native = self.pricing._fetch_defillama("trx", ["coingecko:tron"])
        trx_info = llama_native.get("tron") or llama_native.get("coingecko:tron") or {}
        trx_price = float(trx_info["price"]) if trx_info.get("price") is not None else None

        portfolio.holdings.append(
            Holding(
                symbol="TRX",
                name="Tron",
                balance=trx_balance,
                decimals=6,
                contract_address=None,
                price_usd=trx_price,
                is_native=True,
                chain="tron",
            )
        )

        # 2. Parse TRC-20 tokens
        trc20_entries = account_data.get("trc20", [])
        raw_trc20_balances: Dict[str, int] = {}
        for entry in trc20_entries:
            if isinstance(entry, dict):
                for contract, bal_val in entry.items():
                    try:
                        raw_trc20_balances[contract] = int(bal_val)
                    except (ValueError, TypeError):
                        pass

        if not raw_trc20_balances:
            return portfolio

        # Batch fetch TRC-20 prices from DefiLlama and DexScreener
        token_contracts = list(raw_trc20_balances.keys())
        prices_map = self.pricing.get_prices("tron", token_contracts)

        for contract, raw_bal in raw_trc20_balances.items():
            known = KNOWN_TRC20.get(contract, {})
            price_info = prices_map.get(contract, {})

            decimals_val = price_info.get("decimals") or known.get("decimals") or 6
            try:
                decimals = int(decimals_val)
            except (ValueError, TypeError):
                decimals = 6

            token_balance = raw_bal / (10 ** decimals)
            symbol = str(price_info.get("symbol") or known.get("symbol") or contract[:6].upper())
            name = str(known.get("name") or price_info.get("name") or symbol)
            price_usd = float(price_info["price"]) if price_info.get("price") is not None else None

            portfolio.holdings.append(
                Holding(
                    symbol=symbol,
                    name=name,
                    balance=token_balance,
                    decimals=decimals,
                    contract_address=contract,
                    price_usd=price_usd,
                    is_native=False,
                    chain="tron",
                )
            )

        return portfolio

    def _fetch_account(self, address: str) -> Optional[dict]:
        url = self.TRONGRID_URL.format(address=address)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
                if resp.status_code == 200:
                    data = resp.json()
                    accounts = data.get("data", [])
                    if accounts and isinstance(accounts, list):
                        return accounts[0]
        except Exception:
            pass
        return None
