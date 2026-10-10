from unittest.mock import MagicMock
from wallet_look.cost_basis import (
    apply_cost_basis,
    infer_cost_basis_all,
    infer_from_evm,
    infer_from_hyperliquid,
    infer_from_solana,
    parse_cost_basis_arg,
)
from wallet_look.models import Holding, Portfolio


def test_parse_cost_basis_arg():
    assert parse_cost_basis_arg("") == {}
    assert parse_cost_basis_arg("   ") == {}

    parsed1 = parse_cost_basis_arg("ETH:2500,SOL:140")
    assert parsed1 == {"ETH": 2500.0, "SOL": 140.0}

    parsed2 = parse_cost_basis_arg("btc=65,000.50  eth:$3,200  sol:145.2")
    assert parsed2 == {"BTC": 65000.5, "ETH": 3200.0, "SOL": 145.2}

    parsed3 = parse_cost_basis_arg("invalid,bad:notanumber,OK:10")
    assert parsed3 == {"OK": 10.0}


def test_apply_cost_basis():
    h1 = Holding(symbol="ETH", name="Ethereum", balance=2.0, price_usd=3000.0)
    h2 = Holding(symbol="SOL", name="Solana", balance=10.0, price_usd=100.0)
    h3 = Holding(symbol="ETH-PERP (LONG)", name="ETH Perp", balance=1.0, price_usd=3000.0)
    h4 = Holding(symbol="PEPE", name="Pepe", balance=1000.0, price_usd=0.001)

    port = Portfolio(address="0xabc", chain="ethereum", holdings=[h1, h2, h3, h4])
    apply_cost_basis([port], {"ETH": 2000.0, "SOL": 150.0})

    assert h1.cost_basis == 2000.0
    assert h1.cost_total_usd == 4000.0
    assert h1.pnl_usd == 2000.0
    assert h1.pnl_pct == 50.0

    assert h2.cost_basis == 150.0
    assert h2.cost_total_usd == 1500.0
    assert h2.pnl_usd == -500.0
    assert h2.pnl_pct == round(((100.0 - 150.0) / 150.0) * 100, 2)

    # Base symbol matching for perps
    assert h3.cost_basis == 2000.0
    assert h3.cost_total_usd == 2000.0
    assert h3.pnl_usd == 1000.0

    # PEPE was not in cost map
    assert h4.cost_basis is None
    assert h4.pnl_usd is None


def test_infer_from_hyperliquid(monkeypatch):
    mock_fills = [
        {
            "side": "B",
            "coin": "PURR",
            "px": "0.20",
            "sz": "1000.0",
            "oid": 101,
        },
        {
            "side": "B",
            "coin": "PURR",
            "px": "0.30",
            "sz": "1000.0",
            "oid": 102,
        },
        {
            "side": "A",  # Sell fill, should be ignored
            "coin": "PURR",
            "px": "0.40",
            "sz": "500.0",
            "oid": 103,
        },
    ]

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json, headers):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_fills
            return mock_resp

    monkeypatch.setattr("httpx.Client", MockClient)

    res = infer_from_hyperliquid("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert "PURR" in res
    inf = res["PURR"]
    assert inf.symbol == "PURR"
    assert inf.total_bought == 2000.0
    assert inf.total_spent_usd == 500.0  # (0.2 * 1000) + (0.3 * 1000) = 200 + 300 = 500
    assert inf.avg_price == 0.25
    assert inf.tx_count == 2
    assert inf.chain == "hyperliquid"


def test_infer_from_evm(monkeypatch):
    user_addr = "0xd8da6bf26964af9d7eed9e03e53415d37aa96045"
    mock_history = {
        "operations": [
            # Tx 1: Sent 1000 USDC, received 100 UNI
            {
                "transactionHash": "0xtx1",
                "from": user_addr,
                "to": "0xpool",
                "tokenInfo": {"symbol": "USDC", "decimals": "6"},
                "value": "1000000000",  # 1000 USDC
            },
            {
                "transactionHash": "0xtx1",
                "from": "0xpool",
                "to": user_addr,
                "tokenInfo": {"symbol": "UNI", "decimals": "18"},
                "value": "100000000000000000000",  # 100 UNI
            },
            # Tx 2: Normal transfer (no stablecoin)
            {
                "transactionHash": "0xtx2",
                "from": "0xfriend",
                "to": user_addr,
                "tokenInfo": {"symbol": "SHIB", "decimals": "18"},
                "value": "500000000000000000000",
            },
        ]
    }

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, headers):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_history
            return mock_resp

    monkeypatch.setattr("httpx.Client", MockClient)

    res = infer_from_evm(user_addr)
    assert "UNI" in res
    inf = res["UNI"]
    assert inf.symbol == "UNI"
    assert inf.avg_price == 10.0  # 1000 USDC / 100 UNI
    assert inf.total_bought == 100.0
    assert inf.total_spent_usd == 1000.0
    assert inf.tx_count == 1
    assert "SHIB" not in res


def test_infer_from_solana(monkeypatch):
    user_addr = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
    usdc_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    token_mint = "TokenMint1111111111111111111111111111111111"

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json, headers):
            method = json.get("method")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if method == "getSignaturesForAddress":
                mock_resp.json.return_value = {"result": [{"signature": "sig123"}]}
            elif method == "getTransaction":
                mock_resp.json.return_value = {
                    "result": {
                        "meta": {
                            "preTokenBalances": [
                                {
                                    "owner": user_addr,
                                    "mint": usdc_mint,
                                    "uiTokenAmount": {"uiAmount": 500.0},
                                },
                                {
                                    "owner": user_addr,
                                    "mint": token_mint,
                                    "uiTokenAmount": {"uiAmount": 0.0},
                                },
                            ],
                            "postTokenBalances": [
                                {
                                    "owner": user_addr,
                                    "mint": usdc_mint,
                                    "uiTokenAmount": {"uiAmount": 200.0},  # Spent 300 USDC
                                },
                                {
                                    "owner": user_addr,
                                    "mint": token_mint,
                                    "uiTokenAmount": {"uiAmount": 10.0},  # Bought 10 tokens
                                },
                            ],
                        }
                    }
                }
            return mock_resp

    monkeypatch.setattr("httpx.Client", MockClient)
    monkeypatch.setattr(
        "wallet_look.pricing.PricingClient.get_prices",
        lambda self, chain, mints: {token_mint: {"symbol": "MYTOK", "price": 30.0}},
    )

    res = infer_from_solana(user_addr)
    assert "MYTOK" in res
    inf = res["MYTOK"]
    assert inf.symbol == "MYTOK"
    assert inf.contract_address == token_mint
    assert inf.total_bought == 10.0
    assert inf.total_spent_usd == 300.0
    assert inf.avg_price == 30.0  # 300 / 10


def test_apply_cost_basis_by_contract_address():
    mint = "HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3"
    h1 = Holding(
        symbol="PYTH",
        name="pyth",
        balance=1000.0,
        price_usd=0.10,
        contract_address=mint,
        chain="solana",
    )
    port = Portfolio(address="Eya9...", chain="solana", holdings=[h1])

    # 1. Match by full mint address
    apply_cost_basis([port], {mint: 0.08})
    assert h1.cost_basis == 0.08
    assert h1.cost_total_usd == 80.0
    assert h1.pnl_usd == 20.0  # 100 - 80

    # 2. Match by short 4-char mint address (e.g. HZ1J...BCt3)
    short_4 = f"{mint[:4]}...{mint[-4:]}"
    h1.cost_basis = None
    h1.cost_total_usd = None
    h1.pnl_usd = None
    apply_cost_basis([port], {short_4: 0.07})
    assert h1.cost_basis == 0.07
    assert h1.pnl_usd == 30.0  # 100 - 70

    # 3. Match by short 6-char mint address (e.g. HZ1Jov...BCt3)
    short_6 = f"{mint[:6]}...{mint[-4:]}"
    h1.cost_basis = None
    apply_cost_basis([port], {short_6: 0.06})
    assert h1.cost_basis == 0.06
    assert h1.pnl_usd == 40.0


def test_infer_cost_basis_all(monkeypatch):
    monkeypatch.setattr(
        "wallet_look.cost_basis.infer_from_hyperliquid",
        lambda addr, timeout=10.0: {},
    )
    monkeypatch.setattr(
        "wallet_look.cost_basis.infer_from_evm",
        lambda addr, timeout=10.0: {},
    )
    monkeypatch.setattr(
        "wallet_look.cost_basis.infer_from_solana",
        lambda addr, timeout=10.0: {},
    )

    merged = infer_cost_basis_all(["0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"])
    assert isinstance(merged, dict)
