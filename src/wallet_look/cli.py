import argparse
import sys

from rich.console import Console

from wallet_look.chains import get_fetcher
from wallet_look.detector import detect_chain
from wallet_look.display import render_portfolio
from wallet_look.models import ChainType

err_console = Console(stderr=True)


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wallet-look",
        description="Inspect cryptocurrency wallet portfolios (ETH, SOL, BTC, etc.) with real-time USD prices.",
    )
    parser.add_argument(
        "address",
        help="Public wallet address (Ethereum 0x..., Solana Base58, Bitcoin 1.../3.../bc1...)",
    )
    parser.add_argument(
        "-c",
        "--chain",
        choices=["auto", "eth", "ethereum", "sol", "solana", "btc", "bitcoin"],
        default="auto",
        help="Target blockchain (default: auto-detect)",
    )
    parser.add_argument(
        "-m",
        "--min-value",
        type=float,
        default=0.0,
        help="Minimum USD value to display (default: 0.0)",
    )
    parser.add_argument(
        "--show-zero",
        action="store_true",
        help="Include holdings with zero balance (default: hidden)",
    )
    parser.add_argument(
        "-s",
        "--sort",
        choices=["value", "balance", "symbol"],
        default="value",
        help="Sort holdings by: value (default), balance, or symbol",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted terminal table",
    )
    return parser.parse_args(args)


def main(args=None) -> int:
    parsed = parse_args(args)
    address = parsed.address.strip()

    # Determine chain
    if parsed.chain == "auto":
        try:
            chain = detect_chain(address)
        except ValueError as err:
            err_console.print(f"[bold red]Error:[/bold red] {err}")
            return 1
    else:
        chain_map = {
            "eth": ChainType.ETHEREUM,
            "ethereum": ChainType.ETHEREUM,
            "sol": ChainType.SOLANA,
            "solana": ChainType.SOLANA,
            "btc": ChainType.BITCOIN,
            "bitcoin": ChainType.BITCOIN,
        }
        chain = chain_map.get(parsed.chain.lower(), ChainType.ETHEREUM)

    if not parsed.json:
        err_console.print(f"[dim]Fetching holdings for {address} on {chain.value.capitalize()}...[/dim]")

    try:
        fetcher = get_fetcher(chain)
        portfolio = fetcher.fetch_portfolio(address)
    except Exception as exc:
        err_console.print(f"[bold red]Failed to fetch portfolio:[/bold red] {exc}")
        return 1

    render_portfolio(
        portfolio=portfolio,
        min_usd=parsed.min_value,
        hide_zero=not parsed.show_zero,
        sort_by=parsed.sort,
        as_json=parsed.json,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
