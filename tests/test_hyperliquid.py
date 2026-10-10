from unittest.mock import MagicMock
from wallet_look.chains.hyperliquid import HyperliquidFetcher


def test_hyperliquid_fetcher(monkeypatch):
    fetcher = HyperliquidFetcher()

    mock_spot = {
        "balances": [
            {"coin": "USDC", "token": 0, "total": "100.0"},
            {"coin": "HYPE", "token": 150, "total": "50.0"},
        ]
    }
    mock_perp = {
        "marginSummary": {"accountValue": "250.0"},
        "assetPositions": [
            {
                "position": {
                    "coin": "ETH",
                    "szi": "1.5",
                    "positionValue": "3750.0",
                    "entryPx": "2500.0",
                }
            }
        ],
    }
    mock_meta = [
        {"tokens": [{"name": "USDC", "index": 0}, {"name": "HYPE", "index": 150}], "universe": [{"tokens": [150, 0]}]},
        [{"midPx": "2.0"}],
    ]

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json, headers):
            req_type = json.get("type")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if req_type == "spotClearinghouseState":
                mock_resp.json.return_value = mock_spot
            elif req_type == "clearinghouseState":
                mock_resp.json.return_value = mock_perp
            elif req_type == "spotMetaAndAssetCtxs":
                mock_resp.json.return_value = mock_meta
            return mock_resp

    monkeypatch.setattr("httpx.Client", MockClient)

    portfolio = fetcher.fetch_portfolio("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
    assert portfolio.chain == "hyperliquid"
    assert len(portfolio.holdings) == 4

    usdc_spot = next(h for h in portfolio.holdings if h.symbol == "USDC")
    assert usdc_spot.balance == 100.0
    assert usdc_spot.price_usd == 1.0

    hype_spot = next(h for h in portfolio.holdings if h.symbol == "HYPE")
    assert hype_spot.balance == 50.0
    assert hype_spot.price_usd == 2.0
    assert hype_spot.value_usd == 100.0

    perp_margin = next(h for h in portfolio.holdings if "Perps" in h.name)
    assert perp_margin.balance == 250.0

    perp_pos = next(h for h in portfolio.holdings if "ETH-PERP" in h.symbol)
    assert perp_pos.balance == 1.5
    assert perp_pos.value_usd == 3750.0
