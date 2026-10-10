import json
from wallet_look.cli import main, parse_args
from wallet_look.models import Holding, Portfolio


def test_parse_args():
    args = parse_args(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--chain", "eth", "-m", "50", "--json"])
    assert args.address == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert args.chain == "eth"
    assert args.min_value == 50.0
    assert args.json is True


def test_cli_main_success(monkeypatch, capsys):
    mock_portfolio = Portfolio(
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

    class MockFetcher:
        def fetch_portfolio(self, address):
            return mock_portfolio

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher())

    # Test JSON output
    code = main(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--json"])
    assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["address"] == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert data["total_usd"] == 5000.0
    assert len(data["holdings"]) == 1


def test_cli_main_invalid_address(capsys):
    code = main(["invalid_crypto_address"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Unable to auto-detect blockchain" in captured.err
