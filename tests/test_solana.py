from wallet_look.chains.solana import SolanaFetcher, WRAPPED_SOL_MINT


def test_solana_fetcher(monkeypatch):
    fetcher = SolanaFetcher()

    # Mock native balance (10 SOL)
    monkeypatch.setattr(fetcher, "_fetch_native_balance", lambda addr: 10.0)

    # Mock token accounts
    mock_token_accounts = [
        {
            "account": {
                "data": {
                    "parsed": {
                        "info": {
                            "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                            "tokenAmount": {
                                "amount": "100000000",
                                "decimals": 6,
                                "uiAmount": 100.0,
                            },
                        }
                    }
                }
            }
        }
    ]

    monkeypatch.setattr(fetcher, "_fetch_token_accounts", lambda addr, prog: mock_token_accounts if "Tokenkeg" in prog else [])

    # Mock pricing
    mock_prices = {
        WRAPPED_SOL_MINT: {"price": 150.0, "symbol": "SOL"},
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": {
            "price": 1.0,
            "symbol": "USDC",
            "name": "USD Coin",
        },
    }
    monkeypatch.setattr(fetcher.pricing, "get_prices", lambda chain, mints: mock_prices)

    portfolio = fetcher.fetch_portfolio("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM")

    assert portfolio.chain == "solana"
    assert len(portfolio.holdings) == 2

    sol_holding = portfolio.holdings[0]
    assert sol_holding.symbol == "SOL"
    assert sol_holding.balance == 10.0
    assert sol_holding.price_usd == 150.0
    assert sol_holding.value_usd == 1500.0
    assert sol_holding.is_native is True

    usdc_holding = portfolio.holdings[1]
    assert usdc_holding.symbol == "USDC"
    assert usdc_holding.balance == 100.0
    assert usdc_holding.price_usd == 1.0
    assert usdc_holding.value_usd == 100.0

    assert portfolio.total_usd == 1600.0
