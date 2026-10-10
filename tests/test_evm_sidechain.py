from wallet_look.chains import SIDECHAIN_CONFIGS, get_fetcher
from wallet_look.chains.evm_sidechain import EvmSidechainFetcher


def test_evm_sidechain_fetcher(monkeypatch):
    config = SIDECHAIN_CONFIGS["arbitrum"]
    fetcher = EvmSidechainFetcher(config)

    # Mock native balance (1.5 ETH)
    monkeypatch.setattr(fetcher, "_fetch_native_balance", lambda addr: 1.5)

    # Mock ERC-20 token balance (100 USDC)
    def mock_token_bal(user, contract, decimals):
        if "af88d0" in contract.lower():  # USDC
            return 100.0
        return 0.0

    monkeypatch.setattr(fetcher, "_fetch_token_balance", mock_token_bal)

    # Mock pricing
    monkeypatch.setattr(
        fetcher.pricing,
        "_fetch_defillama",
        lambda chain, ids: {"ethereum:0x0000000000000000000000000000000000000000": {"price": 2500.0}},
    )
    monkeypatch.setattr(
        fetcher.pricing,
        "get_prices",
        lambda chain, addrs: {"0xaf88d065e77c8cc2239327c5edb3a432268e5831": {"price": 1.0}},
    )

    portfolio = fetcher.fetch_portfolio("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert portfolio.chain == "arbitrum"

    eth = next(h for h in portfolio.holdings if h.symbol == "ETH")
    assert eth.balance == 1.5
    assert eth.price_usd == 2500.0
    assert eth.value_usd == 3750.0

    usdc = next(h for h in portfolio.holdings if h.symbol == "USDC")
    assert usdc.balance == 100.0
    assert usdc.price_usd == 1.0
    assert usdc.value_usd == 100.0


def test_get_fetcher_sidechains():
    assert get_fetcher("arbitrum").config.chain_id == "arbitrum"
    assert get_fetcher("base").config.chain_id == "base"
    assert get_fetcher("optimism").config.chain_id == "optimism"
    assert get_fetcher("polygon").config.chain_id == "polygon"
    assert get_fetcher("bsc").config.chain_id == "bsc"
    assert get_fetcher("avalanche").config.chain_id == "avalanche"
    assert get_fetcher("hyperevm").config.chain_id == "hyperevm"
    assert get_fetcher("hyperliquid").INFO_URL == "https://api.hyperliquid.xyz/info"
