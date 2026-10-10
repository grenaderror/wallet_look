import json
from wallet_look.display import (
    _build_consolidated_table,
    _get_token_type,
    format_chain_name,
    render_portfolio,
    render_portfolios,
)
from wallet_look.models import Holding, Portfolio


def test_format_chain_name():
    assert format_chain_name("ethereum") == "Ethereum"
    assert format_chain_name("eth") == "Ethereum"
    assert format_chain_name("solana") == "Solana"
    assert format_chain_name("arbitrum") == "Arbitrum"
    assert format_chain_name("bsc") == "BSC"
    assert format_chain_name("hyperevm") == "HyperEVM"
    assert format_chain_name("tron") == "TRON"
    assert format_chain_name("sui") == "SUI"
    assert format_chain_name("custom_chain") == "Custom_chain"


def test_get_token_type():
    h_native = Holding(symbol="ETH", name="Ethereum", balance=1.0, is_native=True)
    assert _get_token_type(h_native, "ethereum") == "Native"

    h_erc20 = Holding(symbol="USDC", name="USD Coin", balance=1.0, is_native=False)
    assert _get_token_type(h_erc20, "ethereum") == "ERC-20"
    assert _get_token_type(h_erc20, "arbitrum") == "ERC-20"
    assert _get_token_type(h_erc20, "bsc") == "BEP-20"
    assert _get_token_type(h_erc20, "tron") == "TRC-20"
    assert _get_token_type(h_erc20, "sui") == "Coin"
    assert _get_token_type(h_erc20, "solana") == "SPL"

    h_hl_spot = Holding(symbol="PURR", name="PURR", balance=10.0, is_native=False)
    assert _get_token_type(h_hl_spot, "hyperliquid") == "Spot"

    h_hl_perp = Holding(symbol="BTC-PERP (LONG)", name="BTC Perp", balance=1.0, is_native=False)
    assert _get_token_type(h_hl_perp, "hyperliquid") == "Perp"

    h_hl_margin = Holding(symbol="USDC (Perps)", name="Hyperliquid Perps Margin Equity", balance=100.0, is_native=False)
    assert _get_token_type(h_hl_margin, "hyperliquid") == "Margin"


def test_build_consolidated_table():
    p1 = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
    )
    p2 = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
    )
    h1 = Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2500.0, is_native=True)
    h2 = Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, is_native=True)

    items = [(p1, h1), (p2, h2)]
    table = _build_consolidated_table(
        items=items,
        combined_total=6500.0,
        table_title="Consolidated Holdings — $6,500.00 USD",
        show_wallet=True,
    )
    assert table.title == "Consolidated Holdings — $6,500.00 USD"
    col_names = [c.header for c in table.columns]
    assert "Chain" in col_names
    assert "Wallet" in col_names
    assert "Asset" in col_names
    assert "Value (USD)" in col_names
    assert "Share" in col_names
    assert table.row_count == 2


def test_render_portfolios_single_table(capsys):
    p_eth = Portfolio(
        address="0x1111111111111111111111111111111111111111",
        chain="ethereum",
        holdings=[Holding(symbol="ETH", name="Ethereum", balance=1.0, price_usd=3000.0, is_native=True)],
    )
    p_arb = Portfolio(
        address="0x1111111111111111111111111111111111111111",
        chain="arbitrum",
        holdings=[Holding(symbol="ARB", name="Arbitrum", balance=500.0, price_usd=1.0, is_native=False)],
    )

    render_portfolios(
        portfolios=[p_eth, p_arb],
        single_table=True,
    )
    # Shouldn't fail, check output
    # Since both portfolios share the same address, Wallet column is omitted
    pass


def test_render_portfolios_single_table_json(capsys):
    p_eth = Portfolio(
        address="0x1111111111111111111111111111111111111111",
        chain="ethereum",
        holdings=[Holding(symbol="ETH", name="Ethereum", balance=1.0, price_usd=3000.0, is_native=True)],
    )
    p_sol = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
        holdings=[Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, is_native=True)],
    )

    render_portfolios(
        portfolios=[p_eth, p_sol],
        single_table=True,
        as_json=True,
    )
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["combined_total_usd"] == 4500.0
    assert data["wallets_count"] == 2
    assert data["holdings_count"] == 2
    assert data["holdings"][0]["symbol"] == "ETH"
    assert data["holdings"][0]["chain"] == "ethereum"
    assert data["holdings"][0]["address"] == "0x1111111111111111111111111111111111111111"
    assert data["holdings"][1]["symbol"] == "SOL"
    assert data["holdings"][1]["chain"] == "solana"


def test_render_portfolio_backwards_compatible_delegation(capsys):
    p = Portfolio(
        address="0x1111111111111111111111111111111111111111",
        chain="ethereum",
        holdings=[Holding(symbol="ETH", name="Ethereum", balance=1.0, price_usd=3000.0, is_native=True)],
    )
    render_portfolio(p, single_table=True, as_json=True)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["combined_total_usd"] == 3000.0
    assert data["holdings_count"] == 1
