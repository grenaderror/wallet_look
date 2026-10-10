import pytest
from unittest.mock import patch, MagicMock
from wallet_look.chains.tron import TronFetcher
from wallet_look.chains import get_fetcher


def test_get_fetcher_tron():
    fetcher = get_fetcher("tron")
    assert isinstance(fetcher, TronFetcher)
    fetcher_trx = get_fetcher("trx")
    assert isinstance(fetcher_trx, TronFetcher)


def test_tron_fetch_portfolio_success():
    fetcher = TronFetcher()

    mock_account_data = {
        "success": True,
        "data": [
            {
                "address": "41a614f7fc96d13b8da1d2304ddbf40e89cf728b7c",
                "balance": 150000000,  # 150 TRX (150 * 10^6 SUN)
                "trc20": [
                    {
                        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": "500000000"  # 500 USDT (6 decimals)
                    }
                ],
            }
        ],
    }

    mock_llama_prices = {
        "coingecko:tron": {"price": 0.30, "symbol": "TRX"},
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": {"price": 1.0, "symbol": "USDT", "decimals": 6},
    }

    with patch.object(fetcher, "_fetch_account", return_value=mock_account_data["data"][0]):
        with patch.object(fetcher.pricing, "_fetch_defillama", return_value=mock_llama_prices):
            with patch.object(fetcher.pricing, "get_prices", return_value=mock_llama_prices):
                portfolio = fetcher.fetch_portfolio("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")

    assert portfolio.chain == "tron"
    assert len(portfolio.holdings) == 2

    # Check TRX native holding
    trx_holding = next(h for h in portfolio.holdings if h.symbol == "TRX")
    assert trx_holding.balance == 150.0
    assert trx_holding.is_native is True
    assert trx_holding.price_usd == 0.30
    assert trx_holding.value_usd == pytest.approx(45.0)

    # Check TRC20 USDT holding
    usdt_holding = next(h for h in portfolio.holdings if h.symbol == "USDT")
    assert usdt_holding.balance == 500.0
    assert usdt_holding.is_native is False
    assert usdt_holding.price_usd == 1.0
    assert usdt_holding.value_usd == pytest.approx(500.0)


def test_tron_fetch_portfolio_empty_account():
    fetcher = TronFetcher()

    with patch.object(fetcher, "_fetch_account", return_value=None):
        portfolio = fetcher.fetch_portfolio("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")

    assert portfolio.chain == "tron"
    assert len(portfolio.holdings) == 0
    assert portfolio.total_usd == 0.0
