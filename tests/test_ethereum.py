from unittest.mock import MagicMock
from wallet_look.chains.ethereum import EthereumFetcher


def test_ethereum_fetcher_parse_ethplorer(monkeypatch):
    fetcher = EthereumFetcher()

    mock_ethplorer_data = {
        "ETH": {
            "balance": 1.5,
            "rawBalance": "1500000000000000000",
            "price": {"rate": 3000.0},
        },
        "tokens": [
            {
                "tokenInfo": {
                    "address": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
                    "decimals": "6",
                    "symbol": "USDC",
                    "name": "USD Coin",
                    "price": {"rate": 1.0},
                },
                "balance": 500.0,
                "rawBalance": "500000000",
            }
        ],
    }

    monkeypatch.setattr(fetcher, "_fetch_ethplorer", lambda addr: mock_ethplorer_data)

    portfolio = fetcher.fetch_portfolio("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")

    assert portfolio.chain == "ethereum"
    assert len(portfolio.holdings) == 2

    native_eth = portfolio.holdings[0]
    assert native_eth.symbol == "ETH"
    assert native_eth.balance == 1.5
    assert native_eth.price_usd == 3000.0
    assert native_eth.value_usd == 4500.0
    assert native_eth.is_native is True

    usdc = portfolio.holdings[1]
    assert usdc.symbol == "USDC"
    assert usdc.balance == 500.0
    assert usdc.price_usd == 1.0
    assert usdc.value_usd == 500.0

    assert portfolio.total_usd == 5000.0


def test_ethereum_fetcher_fallback_rpc(monkeypatch):
    fetcher = EthereumFetcher()

    monkeypatch.setattr(fetcher, "_fetch_ethplorer", lambda addr: None)
    monkeypatch.setattr(
        fetcher,
        "_fetch_native_via_rpc",
        lambda addr: fetcher._parse_ethplorer_data(
            addr, {"ETH": {"balance": 2.0, "price": {"rate": 2500.0}}, "tokens": []}
        )[0],
    )

    portfolio = fetcher.fetch_portfolio("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert len(portfolio.holdings) == 1
    assert portfolio.holdings[0].symbol == "ETH"
    assert portfolio.holdings[0].balance == 2.0
