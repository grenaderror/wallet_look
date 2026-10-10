from wallet_look.models import Holding, Portfolio


def test_holding_value_calculation():
    h = Holding(
        symbol="ETH",
        name="Ethereum",
        balance=2.5,
        decimals=18,
        price_usd=2000.0,
    )
    assert h.value_usd == 5000.0


def test_portfolio_total_usd():
    h1 = Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2000.0)
    h2 = Holding(symbol="USDC", name="USD Coin", balance=500.0, price_usd=1.0)
    h3 = Holding(symbol="SHIB", name="Shiba Inu", balance=100.0, price_usd=None)

    portfolio = Portfolio(address="0xabc", chain="ethereum", holdings=[h1, h2, h3])

    assert portfolio.total_usd == 4500.0
    assert portfolio.priced_count == 2
    assert portfolio.unpriced_count == 1


def test_portfolio_filtering_and_sorting():
    h1 = Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2000.0)  # val: 4000
    h2 = Holding(symbol="USDC", name="USD Coin", balance=500.0, price_usd=1.0)  # val: 500
    h3 = Holding(symbol="ZERO", name="Zero Coin", balance=0.0, price_usd=10.0)  # bal: 0
    h4 = Holding(symbol="AAVE", name="Aave", balance=10.0, price_usd=100.0)  # val: 1000

    portfolio = Portfolio(address="0xabc", chain="ethereum", holdings=[h1, h2, h3, h4])

    # Default sort by value desc, hide zero balances
    filtered = portfolio.filter_and_sort(min_usd=0.0, hide_zero=True, sort_by="value")
    assert [h.symbol for h in filtered] == ["ETH", "AAVE", "USDC"]

    # Filter with min_usd = 600
    filtered_min = portfolio.filter_and_sort(min_usd=600.0, hide_zero=True, sort_by="value")
    assert [h.symbol for h in filtered_min] == ["ETH", "AAVE"]

    # Show zero balances
    with_zero = portfolio.filter_and_sort(min_usd=0.0, hide_zero=False, sort_by="value")
    assert "ZERO" in [h.symbol for h in with_zero]

    # Sort by symbol ascending
    sorted_sym = portfolio.filter_and_sort(sort_by="symbol")
    assert [h.symbol for h in sorted_sym] == ["AAVE", "ETH", "USDC"]


def test_portfolio_to_dict():
    h = Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, chain="solana")
    portfolio = Portfolio(address="abc", chain="solana", holdings=[h])
    d = portfolio.to_dict()

    assert d["address"] == "abc"
    assert d["chain"] == "solana"
    assert d["total_usd"] == 1500.0
    assert len(d["holdings"]) == 1
    assert d["holdings"][0]["symbol"] == "SOL"


def test_holding_cost_basis_and_pnl():
    h = Holding(
        symbol="ETH",
        name="Ethereum",
        balance=2.0,
        price_usd=3000.0,
        cost_basis=2000.0,
    )
    assert h.value_usd == 6000.0
    assert h.cost_total_usd == 4000.0
    assert h.pnl_usd == 2000.0
    assert h.pnl_pct == 50.0

    d = h.to_dict()
    assert d["cost_basis"] == 2000.0
    assert d["cost_total_usd"] == 4000.0
    assert d["pnl_usd"] == 2000.0
    assert d["pnl_pct"] == 50.0


def test_portfolio_total_cost_and_pnl():
    h1 = Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=3000.0, cost_basis=2000.0)
    h2 = Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=100.0, cost_basis=150.0)
    h3 = Holding(symbol="USDC", name="USD Coin", balance=500.0, price_usd=1.0)  # No cost basis

    p = Portfolio(address="0xabc", chain="ethereum", holdings=[h1, h2, h3])
    # h1: value = 6000, cost = 4000, pnl = +2000
    # h2: value = 1000, cost = 1500, pnl = -500
    # total cost = 5500, total pnl = +1500
    assert p.total_usd == 7500.0
    assert p.total_cost_usd == 5500.0
    assert p.total_pnl_usd == 1500.0
    assert p.total_pnl_pct == round((1500.0 / 5500.0) * 100, 2)

    # Sort by pnl (holdings with computed PnL appear first ranked desc, followed by undefined)
    sorted_pnl = p.filter_and_sort(sort_by="pnl")
    assert [h.symbol for h in sorted_pnl] == ["ETH", "SOL", "USDC"]


