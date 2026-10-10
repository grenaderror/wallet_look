from __future__ import annotations

from typing import Any, Dict, List, Optional
import httpx

from wallet_look.chains.base import BaseChainFetcher
from wallet_look.models import Holding, Portfolio
from wallet_look.pricing import PricingClient


class EvmSidechainConfig:
    def __init__(
        self,
        chain_id: str,
        display_name: str,
        rpc_urls: List[str],
        native_symbol: str,
        native_name: str,
        defillama_chain: str,
        native_price_chain: str,
        native_price_address: str,
        common_tokens: List[Dict[str, Any]],
    ) -> None:
        self.chain_id = chain_id
        self.display_name = display_name
        self.rpc_urls = rpc_urls
        self.native_symbol = native_symbol
        self.native_name = native_name
        self.defillama_chain = defillama_chain
        self.native_price_chain = native_price_chain
        self.native_price_address = native_price_address
        self.common_tokens = common_tokens


# Configurations for popular EVM sidechains and L2s
SIDECHAIN_CONFIGS: Dict[str, EvmSidechainConfig] = {
    "arbitrum": EvmSidechainConfig(
        chain_id="arbitrum",
        display_name="Arbitrum One",
        rpc_urls=["https://arbitrum-one-rpc.publicnode.com", "https://arb1.arbitrum.io/rpc"],
        native_symbol="ETH",
        native_name="Ethereum",
        defillama_chain="arbitrum",
        native_price_chain="ethereum",
        native_price_address="0x0000000000000000000000000000000000000000",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6},
            {"symbol": "USDT", "name": "Tether USD", "address": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "decimals": 6},
            {"symbol": "ARB", "name": "Arbitrum", "address": "0x912CE59144191C1204E64559FE8253a0e49E6548", "decimals": 18},
            {"symbol": "WETH", "name": "Wrapped Ether", "address": "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1", "decimals": 18},
        ],
    ),
    "base": EvmSidechainConfig(
        chain_id="base",
        display_name="Base",
        rpc_urls=["https://base-rpc.publicnode.com", "https://mainnet.base.org"],
        native_symbol="ETH",
        native_name="Ethereum",
        defillama_chain="base",
        native_price_chain="ethereum",
        native_price_address="0x0000000000000000000000000000000000000000",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6},
            {"symbol": "AERO", "name": "Aerodrome Finance", "address": "0x940181a94A35A4569E4529A3CDfB74e38FD98631", "decimals": 18},
            {"symbol": "WETH", "name": "Wrapped Ether", "address": "0x4200000000000000000000000000000000000006", "decimals": 18},
        ],
    ),
    "optimism": EvmSidechainConfig(
        chain_id="optimism",
        display_name="OP Mainnet",
        rpc_urls=["https://optimism-rpc.publicnode.com", "https://mainnet.optimism.io"],
        native_symbol="ETH",
        native_name="Ethereum",
        defillama_chain="optimism",
        native_price_chain="ethereum",
        native_price_address="0x0000000000000000000000000000000000000000",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85", "decimals": 6},
            {"symbol": "USDT", "name": "Tether USD", "address": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58", "decimals": 6},
            {"symbol": "OP", "name": "Optimism", "address": "0x4200000000000000000000000000000000000042", "decimals": 18},
            {"symbol": "WETH", "name": "Wrapped Ether", "address": "0x4200000000000000000000000000000000000006", "decimals": 18},
        ],
    ),
    "polygon": EvmSidechainConfig(
        chain_id="polygon",
        display_name="Polygon PoS",
        rpc_urls=["https://polygon-bor-rpc.publicnode.com", "https://polygon-rpc.com"],
        native_symbol="POL",
        native_name="Polygon",
        defillama_chain="polygon",
        native_price_chain="polygon",
        native_price_address="0x0000000000000000000000000000000000000000",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "decimals": 6},
            {"symbol": "USDT", "name": "Tether USD", "address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "decimals": 6},
            {"symbol": "WETH", "name": "Wrapped Ether", "address": "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619", "decimals": 18},
        ],
    ),
    "bsc": EvmSidechainConfig(
        chain_id="bsc",
        display_name="BNB Smart Chain",
        rpc_urls=["https://bsc-rpc.publicnode.com", "https://bsc-dataseed.binance.org"],
        native_symbol="BNB",
        native_name="BNB",
        defillama_chain="bsc",
        native_price_chain="coingecko",
        native_price_address="binancecoin",
        common_tokens=[
            {"symbol": "USDT", "name": "Tether USD", "address": "0x55d398326f99059fF775485246999027B3197955", "decimals": 18},
            {"symbol": "USDC", "name": "USD Coin", "address": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18},
            {"symbol": "WBNB", "name": "Wrapped BNB", "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "decimals": 18},
        ],
    ),
    "avalanche": EvmSidechainConfig(
        chain_id="avalanche",
        display_name="Avalanche C-Chain",
        rpc_urls=["https://avalanche-c-chain-rpc.publicnode.com", "https://api.avax.network/ext/bc/C/rpc"],
        native_symbol="AVAX",
        native_name="Avalanche",
        defillama_chain="avax",
        native_price_chain="coingecko",
        native_price_address="avalanche-2",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E", "decimals": 6},
            {"symbol": "USDT", "name": "Tether USD", "address": "0x9719d528232A8062fD2038FE091e4a3b839F80c4", "decimals": 6},
            {"symbol": "WAVAX", "name": "Wrapped AVAX", "address": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7", "decimals": 18},
        ],
    ),
    "hyperevm": EvmSidechainConfig(
        chain_id="hyperevm",
        display_name="HyperEVM",
        rpc_urls=["https://rpc.hyperliquid.xyz/evm"],
        native_symbol="HYPE",
        native_name="Hyperliquid",
        defillama_chain="hyperliquid",
        native_price_chain="coingecko",
        native_price_address="hyperliquid",
        common_tokens=[
            {"symbol": "USDC", "name": "USD Coin", "address": "0xb88339CB7199b77E23DB6E890353E22632Ba630f", "decimals": 6},
            {"symbol": "PURR", "name": "Purr", "address": "0x9b498C3c8A0b8CD8BA1D9851d40D186F1872b44E", "decimals": 18},
        ],
    ),
}


class EvmSidechainFetcher(BaseChainFetcher):
    """Generic fetcher for EVM sidechains and Layer 2 networks."""

    def __init__(self, config: EvmSidechainConfig, timeout: float = 6.0) -> None:
        self.config = config
        self.timeout = timeout
        self.pricing = PricingClient(timeout=timeout)

    def fetch_portfolio(self, address: str) -> Portfolio:
        clean_addr = address.strip()
        portfolio = Portfolio(address=clean_addr, chain=self.config.chain_id)

        # 1. Fetch native balance
        native_bal = self._fetch_native_balance(clean_addr)

        # 2. Fetch ERC-20 balances for common tokens
        token_holdings_raw: List[Dict[str, Any]] = []
        token_addresses_to_price: List[str] = []

        for token in self.config.common_tokens:
            bal = self._fetch_token_balance(clean_addr, token["address"], token["decimals"])
            token_holdings_raw.append({**token, "balance": bal})
            if bal > 0:
                token_addresses_to_price.append(token["address"])

        # 3. Fetch prices for native token and non-zero ERC-20 tokens
        # Native price
        native_price = None
        native_price_map = self.pricing._fetch_defillama(
            self.config.native_price_chain, [self.config.native_price_address]
        )
        for k, v in native_price_map.items():
            if v and v.get("price") is not None:
                native_price = float(v["price"])
                break

        # Token prices
        token_prices_map = {}
        if token_addresses_to_price:
            token_prices_map = self.pricing.get_prices(self.config.defillama_chain, token_addresses_to_price)

        holdings: List[Holding] = [
            Holding(
                symbol=self.config.native_symbol,
                name=self.config.native_name,
                balance=native_bal,
                decimals=18,
                contract_address=None,
                price_usd=native_price,
                is_native=True,
                chain=self.config.chain_id,
            )
        ]

        for item in token_holdings_raw:
            price_info = token_prices_map.get(item["address"].lower()) or token_prices_map.get(item["address"]) or {}
            price_usd = price_info.get("price")
            holdings.append(
                Holding(
                    symbol=item["symbol"],
                    name=item["name"],
                    balance=item["balance"],
                    decimals=item["decimals"],
                    contract_address=item["address"],
                    price_usd=float(price_usd) if price_usd is not None else None,
                    is_native=False,
                    chain=self.config.chain_id,
                )
            )

        portfolio.holdings = holdings
        return portfolio

    def _rpc_call(self, payload: dict) -> Optional[dict]:
        for rpc in self.config.rpc_urls:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        rpc,
                        json=payload,
                        headers={"Content-Type": "application/json", "User-Agent": "wallet-look/0.1"},
                    )
                    if resp.status_code == 200:
                        return resp.json()
            except Exception:
                continue
        return None

    def _fetch_native_balance(self, address: str) -> float:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getBalance",
            "params": [address, "latest"],
        }
        res = self._rpc_call(payload)
        if res and "result" in res:
            try:
                return int(res["result"], 16) / 1e18
            except (ValueError, TypeError):
                pass
        return 0.0

    def _fetch_token_balance(self, user_address: str, contract_address: str, decimals: int) -> float:
        addr_clean = user_address[2:].lower().zfill(64)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [
                {
                    "to": contract_address,
                    "data": f"0x70a08231{addr_clean}",
                },
                "latest",
            ],
        }
        res = self._rpc_call(payload)
        if res and "result" in res:
            try:
                raw_bal = int(res["result"], 16)
                return raw_bal / (10**decimals)
            except (ValueError, TypeError):
                pass
        return 0.0
