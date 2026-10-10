import json
from wallet_look.cli import main, parse_args
from wallet_look.models import ChainType, Holding, Portfolio


def test_parse_args():
    args = parse_args(
        ["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--chain", "eth", "-m", "50", "--json"]
    )
    assert args.address == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert args.chain == "eth"
    assert args.min_value == 50.0
    assert args.json is True
    assert args.no_equivalent is False


def test_cli_main_success(monkeypatch, capsys):
    mock_eth_portfolio = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[
            Holding(
                symbol="ETH",
                name="Ethereum",
                balance=2.0,
                decimals=18,
                price_usd=2500.0,
                is_native=True,
            )
        ],
    )

    mock_sol_portfolio = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
        holdings=[
            Holding(
                symbol="SOL",
                name="Solana",
                balance=10.0,
                decimals=9,
                price_usd=150.0,
                is_native=True,
            )
        ],
    )

    class MockFetcher:
        def __init__(self, chain):
            self.chain = chain

        def fetch_portfolio(self, address):
            if str(self.chain).lower().endswith("solana"):
                return mock_sol_portfolio
            return mock_eth_portfolio

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))
    monkeypatch.setattr(
        "wallet_look.cli.get_equivalent_chain_and_address",
        lambda addr, chain: (
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            ChainType.SOLANA,
            "ENS Record",
        ),
    )

    # Test JSON output includes both primary and equivalent
    code = main(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--json"])
    assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["address"] == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert data["total_usd"] == 5000.0
    assert "equivalent" in data
    assert data["equivalent"]["address"] == "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    assert data["equivalent"]["chain"] == "solana"
    assert data["equivalent"]["total_usd"] == 1500.0
    assert data["combined_total_usd"] == 6500.0


def test_cli_main_invalid_address(capsys):
    code = main(["invalid_crypto_address"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Unable to auto-detect blockchain" in captured.err
