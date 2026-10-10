import argparse
import sys
from typing import List

from rich.console import Console

from wallet_look.chains import get_fetcher
from wallet_look.cross_chain import get_equivalent_chain_and_address
from wallet_look.detector import detect_chain
from wallet_look.display import render_portfolios
from wallet_look.models import ChainType, Portfolio
from wallet_look.profiles import get_profile, list_profiles as _raw_list, load_profiles, save_profile

err_console = Console(stderr=True)


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wallet-look",
        description="Inspect cryptocurrency wallet portfolios (ETH, SOL, BTC) with real-time USD prices across multiple chains.",
    )
    parser.add_argument(
        "addresses",
        nargs="*",
        help="One or more wallet addresses (e.g. your SOL address and ETH address)",
    )
    parser.add_argument(
        "--eth",
        help="Explicit Ethereum address to include",
    )
    parser.add_argument(
        "--sol",
        help="Explicit Solana address to include",
    )
    parser.add_argument(
        "--btc",
        help="Explicit Bitcoin address to include",
    )
    parser.add_argument(
        "-p",
        "--profile",
        help="Load saved wallet profile by name (e.g. --profile mywallet)",
    )
    parser.add_argument(
        "--save",
        metavar="PROFILE_NAME",
        help="Save the provided addresses to a named profile for easy future lookups",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all saved wallet profiles and exit",
    )
    parser.add_argument(
        "-c",
        "--chain",
        choices=["auto", "eth", "ethereum", "sol", "solana", "btc", "bitcoin"],
        default="auto",
        help="Force specific blockchain for a single address (default: auto-detect)",
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
        "--no-equivalent",
        action="store_true",
        help="Disable automatic cross-chain equivalent address fallback for single address lookups",
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

    # 1. Handle --list-profiles
    if parsed.list_profiles:
        profiles = load_profiles()
        if not profiles:
            err_console.print("[dim]No saved wallet profiles found. Save one with: wallet-look <addr1> <addr2> --save mywallet[/dim]")
            return 0
        err_console.print("[bold yellow]Saved Wallet Profiles:[/bold yellow]")
        for name, addrs in profiles.items():
            err_console.print(f"  [bold cyan]{name}[/bold cyan]: {', '.join(addrs)}")
        return 0

    # 2. Collect all target addresses
    target_addresses: List[str] = []

    # From profile
    if parsed.profile:
        loaded = get_profile(parsed.profile)
        if not loaded:
            err_console.print(f"[bold red]Error:[/bold red] Profile '{parsed.profile}' not found.")
            return 1
        target_addresses.extend(loaded)

    # From positional arguments
    if parsed.addresses:
        target_addresses.extend(parsed.addresses)

    # From specific flags
    if parsed.eth:
        target_addresses.append(parsed.eth.strip())
    if parsed.sol:
        target_addresses.append(parsed.sol.strip())
    if parsed.btc:
        target_addresses.append(parsed.btc.strip())

    # Deduplicate while preserving order
    target_addresses = list(dict.fromkeys(a.strip() for a in target_addresses if a.strip()))

    if not target_addresses:
        err_console.print(
            "[bold red]Error:[/bold red] Please provide at least one wallet address (or --profile / --eth / --sol)."
        )
        return 1

    # 3. Handle --save profile
    if parsed.save:
        save_profile(parsed.save, target_addresses)
        if not parsed.json:
            err_console.print(
                f"[bold green]Saved profile '{parsed.save}' with {len(target_addresses)} addresses![/bold green]"
            )

    # 4. Fetch portfolios
    portfolios: List[Portfolio] = []

    # Case A: If user provided multiple addresses (e.g. their SOL and ETH addresses)
    if len(target_addresses) > 1:
        for addr in target_addresses:
            try:
                ch = detect_chain(addr)
            except ValueError as err:
                err_console.print(f"[dim yellow]Warning skipping invalid address: {err}[/dim yellow]")
                continue

            if not parsed.json:
                err_console.print(f"[dim]Fetching holdings for {addr} on {ch.value.capitalize()}...[/dim]")
            try:
                fetcher = get_fetcher(ch)
                portfolios.append(fetcher.fetch_portfolio(addr))
            except Exception as exc:
                err_console.print(f"[dim red]Failed to fetch portfolio for {addr}: {exc}[/dim red]")

    # Case B: Single address provided
    else:
        addr = target_addresses[0]
        if parsed.chain == "auto":
            try:
                ch = detect_chain(addr)
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
            ch = chain_map.get(parsed.chain.lower(), ChainType.ETHEREUM)

        if not parsed.json:
            err_console.print(f"[dim]Fetching holdings for {addr} on {ch.value.capitalize()}...[/dim]")
        try:
            fetcher = get_fetcher(ch)
            primary_portfolio = fetcher.fetch_portfolio(addr)
            portfolios.append(primary_portfolio)
        except Exception as exc:
            err_console.print(f"[bold red]Failed to fetch primary portfolio:[/bold red] {exc}")
            return 1

        # Check for cross-chain equivalent address if not disabled
        if not parsed.no_equivalent:
            eq_info = get_equivalent_chain_and_address(addr, ch)
            if eq_info:
                eq_addr, eq_chain, method = eq_info
                if not parsed.json:
                    err_console.print(
                        f"[dim]Checking equivalent {eq_chain.value.capitalize()} address {eq_addr} ({method})...[/dim]"
                    )
                try:
                    eq_fetcher = get_fetcher(eq_chain)
                    eq_p = eq_fetcher.fetch_portfolio(eq_addr)
                    # Only append if it found holdings or if requested
                    portfolios.append(eq_p)
                except Exception:
                    pass

    # 5. Render results
    render_portfolios(
        portfolios=portfolios,
        min_usd=parsed.min_value,
        hide_zero=not parsed.show_zero,
        sort_by=parsed.sort,
        as_json=parsed.json,
        profile_name=parsed.profile or parsed.save,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
