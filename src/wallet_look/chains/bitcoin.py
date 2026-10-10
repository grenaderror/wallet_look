from __future__ import annotations

from typing import Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient


class BitcoinFetcher(BaseChainFetcher):
    """Fetcher for Bitcoin addresses via Blockstream public explorer API."""

    BLOCKSTREAM_URL = "https://blockstream.info/api/address/{address}"

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain="bitcoin")

        satoshis = self._fetch_balance_satoshis(clean_addr)
        btc_balance = satoshis / 1e8

        # Get BTC price
        prices = self.pricing._fetch_defillama("btc", ["bitcoin"])
        btc_price_info = prices.get("coingecko:bitcoin") or prices.get("bitcoin") or {}
        btc_price = btc_price_info.get("price")
        price_val = float(btc_price) if btc_price is not None else None

        portfolio.holdings = [
            Holding(
                symbol="BTC",
                name="Bitcoin",
                balance=btc_balance,
                decimals=8,
                contract_address=None,
                price_usd=price_val,
                is_native=True,
                chain="bitcoin",
            )
        ]
        return portfolio

    def _fetch_balance_satoshis(self, address: str) -> int:
        url = self.BLOCKSTREAM_URL.format(address=address)
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers={"User-Agent": "wallet-look/0.1"})
                if resp.status_code == 200:
                    data = resp.json()
                    c_stats = data.get("chain_stats", {})
                    m_stats = data.get("mempool_stats", {})

                    confirmed = c_stats.get("funded_txo_sum", 0) - c_stats.get("spent_txo_sum", 0)
                    unconfirmed = m_stats.get("funded_txo_sum", 0) - m_stats.get("spent_txo_sum", 0)
                    return max(0, confirmed + unconfirmed)
        except Exception:
            pass
        return 0
