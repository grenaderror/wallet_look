import argparse
from concurrent.futures import ThreadPoolExecutor
import sys
from typing import List

from rich.console import Console

from wallet_look.chains import SIDECHAIN_CONFIGS, get_fetcher
from wallet_look.cross_chain import get_equivalent_chain_and_address
from wallet_look.detector import detect_chain
from wallet_look.display import render_portfolios
from wallet_look.models import ChainType, Portfolio
from wallet_look.profiles import get_profile, load_profiles, save_profile

err_console = Console(stderr=True)

CHAIN_CHOICES = [
    "auto",
    "eth",
    "ethereum",
    "sol",
    "solana",
    "btc",
    "bitcoin",
    "arb",
    "arbitrum",
    "base",
    "op",
    "optimism",
    "polygon",
    "matic",
    "bsc",
    "bnb",
    "avax",
    "avalanche",
    "hl",
    "hyperliquid",
    "hyperevm",
    "hevm",
    "tron",
    "trx",
    "sui",
    "all-evm",
]

EVM_CHAINS_LIST = [
    "ethereum",
    "arbitrum",
    "base",
    "optimism",
    "polygon",
    "bsc",
    "avalanche",
    "hyperliquid",
    "hyperevm",
]


def parse_args(args=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="wallet-look",
        description="Inspect cryptocurrency wallet portfolios (ETH, SOL, BTC, TRON, SUI, EVM Sidechains, Hyperliquid) with real-time USD prices.",
    )
    parser.add_argument(
        "addresses",
        nargs="*",
        help="One or more wallet addresses (e.g. SOL address and ETH address)",
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
        "--tron",
        "--trx",
        dest="tron",
        help="Explicit TRON address to include",
    )
    parser.add_argument(
        "--sui",
        help="Explicit SUI address to include",
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
        choices=CHAIN_CHOICES,
        default="auto",
        help="Target blockchain (default: auto-detect; supports all-evm, hyperliquid, arbitrum, base, etc.)",
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
        "--no-sidechains",
        action="store_true",
        help="Disable automatic EVM sidechain and Hyperliquid scanning for 0x... addresses",
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
        "--single-table",
        "--single",
        dest="single_table",
        action="store_true",
        help="Consolidate all holdings into a single table across all chains and wallets",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted terminal table",
    )
    return parser.parse_args(args)


def _fetch_single_chain_safe(chain_name: str, address: str) -> Portfolio:
    try:
        fetcher = get_fetcher(chain_name)
        return fetcher.fetch_portfolio(address)
    except Exception as exc:
        err_console.print(f"[dim red]Failed to fetch {chain_name} for {address}: {exc}[/dim red]")
        return Portfolio(address=address, chain=chain_name, holdings=[])


def _fetch_evm_multichain(address: str, as_json: bool = False, show_zero: bool = False) -> List[Portfolio]:
    if not as_json:
        err_console.print(
            f"[dim]Scanning Ethereum, sidechains (Arbitrum, Base, OP, Polygon, BSC, Avalanche), and Hyperliquid for {address}...[/dim]"
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        portfolios = list(
            executor.map(lambda ch: _fetch_single_chain_safe(ch, address), EVM_CHAINS_LIST)
        )

    # Filter out empty sidechains unless show_zero is requested
    results: List[Portfolio] = []
    for p in portfolios:
        # Keep Ethereum mainnet and any sidechain that has non-zero total value or holdings
        if p.chain == "ethereum" or p.total_usd > 0 or (show_zero and len(p.holdings) > 0):
            results.append(p)
        elif any(h.balance > 0 for h in p.holdings):
            results.append(p)

    return results


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

    # 2. Collect target addresses
    target_addresses: List[str] = []

    if parsed.profile:
        loaded = get_profile(parsed.profile)
        if not loaded:
            err_console.print(f"[bold red]Error:[/bold red] Profile '{parsed.profile}' not found.")
            return 1
        target_addresses.extend(loaded)

    if parsed.addresses:
        target_addresses.extend(parsed.addresses)

    if parsed.eth:
        target_addresses.append(parsed.eth.strip())
    if parsed.sol:
        target_addresses.append(parsed.sol.strip())
    if parsed.btc:
        target_addresses.append(parsed.btc.strip())
    if parsed.tron:
        target_addresses.append(parsed.tron.strip())
    if parsed.sui:
        target_addresses.append(parsed.sui.strip())

    target_addresses = list(dict.fromkeys(a.strip() for a in target_addresses if a.strip()))

    if not target_addresses:
        err_console.print(
            "[bold red]Error:[/bold red] Please provide at least one wallet address (or --profile / --eth / --sol / --tron / --sui)."
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

    # Case A: Explicit multiple addresses
    if len(target_addresses) > 1:
        for addr in target_addresses:
            try:
                ch = detect_chain(addr)
            except ValueError as err:
                err_console.print(f"[dim yellow]Warning skipping invalid address: {err}[/dim yellow]")
                continue

            if ch == ChainType.ETHEREUM and not parsed.no_sidechains and parsed.chain in ("auto", "all-evm"):
                evm_ports = _fetch_evm_multichain(addr, as_json=parsed.json, show_zero=parsed.show_zero)
                portfolios.extend(evm_ports)
            else:
                if not parsed.json:
                    err_console.print(f"[dim]Fetching holdings for {addr} on {ch.value.capitalize()}...[/dim]")
                portfolios.append(_fetch_single_chain_safe(ch.value, addr))

    # Case B: Single address
    else:
        addr = target_addresses[0]

        # Specific chain requested (e.g. --chain base, --chain hyperliquid, etc.)
        if parsed.chain not in ("auto", "all-evm"):
            if not parsed.json:
                err_console.print(f"[dim]Fetching holdings for {addr} on {parsed.chain.capitalize()}...[/dim]")
            portfolios.append(_fetch_single_chain_safe(parsed.chain, addr))

        else:
            # Auto-detect chain
            try:
                ch = detect_chain(addr)
            except ValueError as err:
                err_console.print(f"[bold red]Error:[/bold red] {err}")
                return 1

            if ch == ChainType.ETHEREUM and not parsed.no_sidechains:
                # Concurrently scan Ethereum + EVM sidechains + Hyperliquid
                evm_ports = _fetch_evm_multichain(addr, as_json=parsed.json, show_zero=parsed.show_zero)
                portfolios.extend(evm_ports)
            else:
                if not parsed.json:
                    err_console.print(f"[dim]Fetching holdings for {addr} on {ch.value.capitalize()}...[/dim]")
                portfolios.append(_fetch_single_chain_safe(ch.value, addr))

            # Cross-chain equivalent address fallback (e.g. SOL -> ETH equivalent)
            if not parsed.no_equivalent and ch == ChainType.SOLANA:
                eq_info = get_equivalent_chain_and_address(addr, ch)
                if eq_info:
                    eq_addr, eq_chain, method = eq_info
                    if not parsed.json:
                        err_console.print(
                            f"[dim]Checking equivalent {eq_chain.value.capitalize()} address {eq_addr} ({method})...[/dim]"
                        )
                    if not parsed.no_sidechains:
                        portfolios.extend(_fetch_evm_multichain(eq_addr, as_json=parsed.json, show_zero=parsed.show_zero))
                    else:
                        portfolios.append(_fetch_single_chain_safe(eq_chain.value, eq_addr))

    # 5. Render results
    render_portfolios(
        portfolios=portfolios,
        min_usd=parsed.min_value,
        hide_zero=not parsed.show_zero,
        sort_by=parsed.sort,
        as_json=parsed.json,
        profile_name=parsed.profile or parsed.save,
        single_table=parsed.single_table,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
