import json
from wallet_look.cli import main, parse_args
from wallet_look.models import ChainType, Holding, Portfolio
from wallet_look.profiles import delete_profile, save_profile


def test_parse_args():
    args = parse_args(
        [
            "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            "--min-value",
            "50",
            "--json",
        ]
    )
    assert len(args.addresses) == 2
    assert args.addresses[0] == "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    assert args.addresses[1] == "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    assert args.min_value == 50.0
    assert args.json is True


def test_cli_multiple_addresses(monkeypatch, capsys):
    mock_eth = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[
            Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2500.0, is_native=True)
        ],
    )
    mock_sol = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
        holdings=[
            Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, is_native=True)
        ],
    )

    class MockFetcher:
        def __init__(self, chain):
            self.chain = chain

        def fetch_portfolio(self, address):
            if str(self.chain).lower().endswith("solana"):
                return mock_sol
            return mock_eth

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))

    code = main([
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "--no-sidechains",
        "--json",
    ])
    assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["combined_total_usd"] == 6500.0
    assert data["wallets_count"] == 2
    assert len(data["wallets"]) == 2


def test_cli_sidechains_scan(monkeypatch, capsys):
    mock_port = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[Holding(symbol="ETH", name="Ethereum", balance=1.0, price_usd=2000.0)],
    )

    class MockFetcher:
        def __init__(self, chain):
            self.chain = chain

        def fetch_portfolio(self, address):
            return Portfolio(
                address=address,
                chain=str(self.chain),
                holdings=[Holding(symbol="TEST", name="Test", balance=1.0, price_usd=10.0)],
            )

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))

    code = main(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--chain", "all-evm", "--json"])
    assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["wallets_count"] == 9
    assert data["combined_total_usd"] == 90.0


def test_cli_profiles(monkeypatch, capsys):
    profile_name = "test_phantom_wallet"
    addrs = [
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    ]
    save_profile(profile_name, addrs)

    mock_port = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[Holding(symbol="ETH", name="Ethereum", balance=1.0, price_usd=2000.0)],
    )

    class MockFetcher:
        def __init__(self, chain):
            pass

        def fetch_portfolio(self, address):
            return mock_port

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))

    code = main(["--profile", profile_name, "--json"])
    assert code == 0

    delete_profile(profile_name)


def test_cli_main_invalid_address(capsys):
    code = main(["invalid_crypto_address"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Unable to auto-detect blockchain" in captured.err


def test_parse_args_single_table():
    args1 = parse_args(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--single-table"])
    assert args1.single_table is True

    args2 = parse_args(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "--single"])
    assert args2.single_table is True

    args3 = parse_args(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"])
    assert args3.single_table is False


def test_cli_single_table_json(monkeypatch, capsys):
    mock_eth = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[
            Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2500.0, is_native=True)
        ],
    )
    mock_sol = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
        holdings=[
            Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, is_native=True)
        ],
    )

    class MockFetcher:
        def __init__(self, chain):
            self.chain = chain

        def fetch_portfolio(self, address):
            if str(self.chain).lower().endswith("solana"):
                return mock_sol
            return mock_eth

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))

    code = main([
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "--single-table",
        "--no-sidechains",
        "--json",
    ])
    assert code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["combined_total_usd"] == 6500.0
    assert data["wallets_count"] == 2
    assert data["holdings_count"] == 2
    assert "holdings" in data
    symbols = [h["symbol"] for h in data["holdings"]]
    assert "ETH" in symbols
    assert "SOL" in symbols


def test_cli_single_table_display(monkeypatch, capsys):
    mock_eth = Portfolio(
        address="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="ethereum",
        holdings=[
            Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=2500.0, is_native=True)
        ],
    )
    mock_sol = Portfolio(
        address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        chain="solana",
        holdings=[
            Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=150.0, is_native=True)
        ],
    )

    class MockFetcher:
        def __init__(self, chain):
            self.chain = chain

        def fetch_portfolio(self, address):
            if str(self.chain).lower().endswith("solana"):
                return mock_sol
            return mock_eth

    monkeypatch.setattr("wallet_look.cli.get_fetcher", lambda chain: MockFetcher(chain))

    code = main([
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "--single-table",
        "--no-sidechains",
    ])
    assert code == 0


