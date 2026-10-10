from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient

SPL_TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"


class SolanaFetcher(BaseChainFetcher):
    """Fetcher for Solana native SOL, SPL tokens, and Token-2022 tokens."""

    PUBLIC_RPCS = [
        "https://api.mainnet-beta.solana.com",
        "https://solana-rpc.publicnode.com",
    ]

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain="solana")

        # 1. Fetch native SOL balance
        sol_balance = self._fetch_native_balance(clean_addr)

        # 2. Fetch SPL token accounts (standard + Token-2022)
        token_accounts = self._fetch_token_accounts(clean_addr, SPL_TOKEN_PROGRAM)
        token_accounts.extend(self._fetch_token_accounts(clean_addr, TOKEN_2022_PROGRAM))

        # 3. Aggregate balances by mint
        # (A wallet might have multiple associated token accounts for the same mint)
        mint_balances: Dict[str, Dict[str, Any]] = {}
        for acc in token_accounts:
            try:
                info = acc["account"]["data"]["parsed"]["info"]
                mint = info["mint"]
                t_amount = info["tokenAmount"]
                decimals = int(t_amount.get("decimals", 0))
                ui_amount = t_amount.get("uiAmount")
                if ui_amount is None:
                    raw_amt = int(t_amount.get("amount", 0))
                    ui_amount = raw_amt / (10**decimals) if decimals > 0 else float(raw_amt)
                else:
                    ui_amount = float(ui_amount)

                if mint not in mint_balances:
                    mint_balances[mint] = {
                        "balance": ui_amount,
                        "decimals": decimals,
                    }
                else:
                    mint_balances[mint]["balance"] += ui_amount
            except Exception:
                continue

        # 4. Fetch prices for native SOL + unique token mints
        # Prioritize tokens with balance > 0 and limit to 100 for fast responsiveness
        non_zero_mints = [m for m, d in mint_balances.items() if d["balance"] > 0]
        zero_mints = [m for m, d in mint_balances.items() if d["balance"] <= 0]
        prioritized_mints = (non_zero_mints + zero_mints)[:100]
        lookup_mints = [WRAPPED_SOL_MINT] + prioritized_mints
        prices_map = self.pricing.get_prices("solana", lookup_mints)

        # Native SOL holding
        sol_price_info = prices_map.get(WRAPPED_SOL_MINT, {})
        sol_price = sol_price_info.get("price") if sol_price_info else None
        sol_price_val = float(sol_price) if sol_price is not None else None

        holdings: List[Holding] = [
            Holding(
                symbol="SOL",
                name="Solana",
                balance=sol_balance,
                decimals=9,
                contract_address=None,
                price_usd=sol_price_val,
                is_native=True,
                chain="solana",
            )
        ]

        # SPL token holdings
        for mint, m_data in mint_balances.items():
            price_info = prices_map.get(mint, {})
            price_val = price_info.get("price")
            price_usd = float(price_val) if price_val is not None else None

            symbol = price_info.get("symbol")
            if not symbol:
                symbol = f"{mint[:4]}...{mint[-4:]}"

            name = price_info.get("name") or symbol

            holdings.append(
                Holding(
                    symbol=symbol.upper(),
                    name=name,
                    balance=m_data["balance"],
                    decimals=m_data["decimals"],
                    contract_address=mint,
                    price_usd=price_usd,
                    is_native=False,
                    chain="solana",
                )
            )

        portfolio.holdings = holdings
        return portfolio

    def _rpc_call(self, method: str, params: list) -> Optional[dict]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        for rpc in self.PUBLIC_RPCS:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        rpc,
                        json=payload,
                        headers={"User-Agent": "wallet-look/0.1", "Content-Type": "application/json"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if "result" in data:
                            return data["result"]
            except Exception:
                continue
        return None

    def _fetch_native_balance(self, address: str) -> float:
        res = self._rpc_call("getBalance", [address])
        if res and isinstance(res, dict) and "value" in res:
            lamports = res["value"]
            return float(lamports) / 1e9
        return 0.0

    def _fetch_token_accounts(self, address: str, program_id: str) -> List[dict]:
        res = self._rpc_call(
            "getTokenAccountsByOwner",
            [
                address,
                {"programId": program_id},
                {"encoding": "jsonParsed"},
            ],
        )
        if res and isinstance(res, dict) and "value" in res:
            return res["value"]
        return []
