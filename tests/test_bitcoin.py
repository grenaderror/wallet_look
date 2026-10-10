from wallet_look.chains.bitcoin import BitcoinFetcher


def test_bitcoin_fetcher(monkeypatch):
    fetcher = BitcoinFetcher()

    # 1 BTC = 100_000_000 satoshis
    monkeypatch.setattr(fetcher, "_fetch_balance_satoshis", lambda addr: 150_000_000)

    # Mock DefiLlama pricing
    monkeypatch.setattr(
        fetcher.pricing,
        "_fetch_defillama",
        lambda chain, tokens: {"coingecko:bitcoin": {"price": 60000.0, "symbol": "BTC"}},
    )

    portfolio = fetcher.fetch_portfolio("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")

    assert portfolio.chain == "bitcoin"
    assert len(portfolio.holdings) == 1
    btc = portfolio.holdings[0]
    assert btc.symbol == "BTC"
    assert btc.balance == 1.5
    assert btc.price_usd == 60000.0
    assert btc.value_usd == 90000.0
    assert portfolio.total_usd == 90000.0
