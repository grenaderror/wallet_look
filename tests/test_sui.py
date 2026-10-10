import pytest
from unittest.mock import patch
from wallet_look.chains.sui import SuiFetcher
from wallet_look.chains import get_fetcher


def test_get_fetcher_sui():
    fetcher = get_fetcher("sui")
    assert isinstance(fetcher, SuiFetcher)


def test_sui_fetch_portfolio_success():
    fetcher = SuiFetcher()

    mock_nodes = [
        {
            "coinType": {
                "repr": "0x0000000000000000000000000000000000000000000000000000000000000002::sui::SUI"
            },
            "totalBalance": "2500000000",  # 2.5 SUI (9 decimals)
        },
        {
            "coinType": {
                "repr": "0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC"
            },
            "totalBalance": "100000000",  # 100 USDC (6 decimals)
        },
    ]

    mock_prices = {
        "coingecko:sui": {"price": 1.20, "symbol": "SUI"},
        "sui:0xdba34672e30cb065b1f93e3ab55318768fd6fef66c15942c9f7cb846e2f900e7::usdc::USDC": {
            "price": 1.0,
            "symbol": "USDC",
            "decimals": 6,
        },
    }

    with patch.object(fetcher, "_fetch_balances", return_value=mock_nodes):
        with patch.object(fetcher.pricing, "_fetch_defillama", return_value=mock_prices):
            portfolio = fetcher.fetch_portfolio(
                "0x0000000000000000000000000000000000000000000000000000000000000002"
            )

    assert portfolio.chain == "sui"
    assert len(portfolio.holdings) == 2

    # Check SUI native holding
    sui_holding = next(h for h in portfolio.holdings if h.symbol == "SUI")
    assert sui_holding.balance == 2.5
    assert sui_holding.is_native is True
    assert sui_holding.decimals == 9
    assert sui_holding.price_usd == 1.20
    assert sui_holding.value_usd == pytest.approx(3.0)

    # Check USDC holding
    usdc_holding = next(h for h in portfolio.holdings if h.symbol == "USDC")
    assert usdc_holding.balance == 100.0
    assert usdc_holding.is_native is False
    assert usdc_holding.decimals == 6
    assert usdc_holding.price_usd == 1.0
    assert usdc_holding.value_usd == pytest.approx(100.0)


def test_sui_fetch_portfolio_empty():
    fetcher = SuiFetcher()

    with patch.object(fetcher, "_fetch_balances", return_value=[]):
        portfolio = fetcher.fetch_portfolio(
            "0x0000000000000000000000000000000000000000000000000000000000000002"
        )

    assert portfolio.chain == "sui"
    assert len(portfolio.holdings) == 0
    assert portfolio.total_usd == 0.0
