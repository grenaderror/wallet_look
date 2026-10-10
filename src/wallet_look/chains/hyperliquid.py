from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient


class HyperliquidFetcher(BaseChainFetcher):
    """Fetcher for Hyperliquid L1 spot token balances and perps account positions."""

    INFO_URL = "https://api.hyperliquid.xyz/info"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip().lower()
        portfolio = Portfolio(address=clean_addr, chain="hyperliquid")

        spot_balances: List[Dict[str, Any]] = []
        margin_summary: Dict[str, Any] = {}
        asset_positions: List[Dict[str, Any]] = []
        token_prices: Dict[int, float] = {0: 1.0}  # USDC is index 0 = $1.00
        token_names: Dict[int, str] = {0: "USD Coin"}

        try:
            with httpx.Client(timeout=self.timeout) as client:
                # 1. Spot Clearinghouse State
                r_spot = client.post(
                    self.INFO_URL,
                    json={"type": "spotClearinghouseState", "user": clean_addr},
                    headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
                )
                if r_spot.status_code == 200:
                    spot_balances = r_spot.json().get("balances", [])

                # 2. Perps Clearinghouse State
                r_perp = client.post(
                    self.INFO_URL,
                    json={"type": "clearinghouseState", "user": clean_addr},
                    headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
                )
                if r_perp.status_code == 200:
                    p_data = r_perp.json()
                    margin_summary = p_data.get("marginSummary", {})
                    asset_positions = p_data.get("assetPositions", [])

                # 3. Spot Metadata and Asset Contexts for live token prices
                r_meta = client.post(
                    self.INFO_URL,
                    json={"type": "spotMetaAndAssetCtxs"},
                    headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
                )
                if r_meta.status_code == 200:
                    meta_raw = r_meta.json()
                    if isinstance(meta_raw, list) and len(meta_raw) >= 2:
                        meta, ctxs = meta_raw[0], meta_raw[1]
                        tokens = meta.get("tokens", [])
                        universe = meta.get("universe", [])

                        for t in tokens:
                            idx = t.get("index")
                            if idx is not None:
                                token_names[idx] = t.get("fullName") or t.get("name") or "Spot Token"

                        for u, ctx in zip(universe, ctxs):
                            u_toks = u.get("tokens", [])
                            if len(u_toks) >= 2:
                                base_idx, quote_idx = u_toks[0], u_toks[1]
                                if quote_idx == 0:  # Paired with USDC
                                    px_str = ctx.get("midPx") or ctx.get("markPx")
                                    if px_str:
                                        try:
                                            token_prices[base_idx] = float(px_str)
                                        except (ValueError, TypeError):
                                            pass
        except Exception:
            pass

        holdings: List[Holding] = []

        # A. Spot Balances
        for b in spot_balances:
            coin = b.get("coin", "UNKNOWN")
            token_idx = b.get("token")
            try:
                total_bal = float(b.get("total", 0.0))
            except (ValueError, TypeError):
                total_bal = 0.0

            price_usd = token_prices.get(token_idx)
            if price_usd is None and coin == "USDC":
                price_usd = 1.0

            name = token_names.get(token_idx) or coin

            holdings.append(
                Holding(
                    symbol=coin,
                    name=name,
                    balance=total_bal,
                    decimals=8,
                    contract_address=f"HL-Token-{token_idx}" if token_idx is not None else None,
                    price_usd=price_usd,
                    is_native=False,
                    chain="hyperliquid",
                )
            )

        # B. Perps Equity Margin
        try:
            account_val = float(margin_summary.get("accountValue", 0.0))
        except (ValueError, TypeError):
            account_val = 0.0

        if account_val > 0:
            holdings.append(
                Holding(
                    symbol="USDC (Perps)",
                    name="Hyperliquid Perps Margin Equity",
                    balance=account_val,
                    decimals=6,
                    contract_address="Hyperliquid Clearinghouse",
                    price_usd=1.0,
                    value_usd=account_val,
                    is_native=False,
                    chain="hyperliquid",
                )
            )

        # C. Active Perp Positions
        for item in asset_positions:
            pos = item.get("position", {})
            coin = pos.get("coin", "")
            try:
                szi = float(pos.get("szi", 0.0))
            except (ValueError, TypeError):
                szi = 0.0

            if szi != 0:
                side = "LONG" if szi > 0 else "SHORT"
                try:
                    pos_val = abs(float(pos.get("positionValue", 0.0)))
                except (ValueError, TypeError):
                    pos_val = 0.0

                unit_px = (pos_val / abs(szi)) if szi != 0 else None

                entry_px = None
                if pos.get("entryPx") is not None:
                    try:
                        entry_px = float(pos.get("entryPx"))
                    except (ValueError, TypeError):
                        pass

                unrealized_pnl = None
                if pos.get("unrealizedPnl") is not None:
                    try:
                        unrealized_pnl = float(pos.get("unrealizedPnl"))
                    except (ValueError, TypeError):
                        pass

                roe_pct = None
                if pos.get("returnOnEquity") is not None:
                    try:
                        roe_pct = round(float(pos.get("returnOnEquity")) * 100, 2)
                    except (ValueError, TypeError):
                        pass

                holdings.append(
                    Holding(
                        symbol=f"{coin}-PERP ({side})",
                        name=f"{coin} Perpetual Position",
                        balance=abs(szi),
                        decimals=4,
                        contract_address=f"{coin}-PERP",
                        price_usd=unit_px,
                        value_usd=pos_val,
                        is_native=False,
                        chain="hyperliquid",
                        cost_basis=entry_px,
                        pnl_usd=unrealized_pnl,
                        pnl_pct=roe_pct,
                    )
                )

        portfolio.holdings = holdings
        return portfolio
