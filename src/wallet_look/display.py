from __future__ import annotations

import json
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from wallet_look.models import Holding, Portfolio

console = Console()


def format_balance(val: float) -> str:
    """Format balance cleanly without excessive precision or scientific notation."""
    if val == 0:
        return "0.00"
    if abs(val) < 0.000001:
        return f"{val:.8f}"
    if abs(val) < 0.01:
        return f"{val:.6f}"
    if abs(val) < 1000:
        return f"{val:,.4f}".rstrip("0").rstrip(".")
    return f"{val:,.2f}"


def format_usd(val: float | None) -> str:
    """Format USD value with appropriate decimals and dollar symbol."""
    if val is None:
        return "[dim]N/A[/dim]"
    if val == 0:
        return "$0.00"
    if val < 0.000001:
        return f"${val:.8f}"
    if val < 0.01:
        return f"${val:.6f}"
    return f"${val:,.2f}"


def render_portfolio(
    portfolio: Portfolio,
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
) -> None:
    """Render the portfolio to the terminal using rich tables or raw JSON."""
    if as_json:
        data = portfolio.to_dict()
        data["holdings"] = [
            h.to_dict()
            for h in portfolio.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by)
        ]
        print(json.dumps(data, indent=2))
        return

    filtered = portfolio.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by)
    total_val = portfolio.total_usd

    # Header Panel
    summary_text = Text()
    summary_text.append("Wallet Address: ", style="bold cyan")
    summary_text.append(f"{portfolio.address}\n", style="white")
    summary_text.append("Blockchain:     ", style="bold cyan")
    summary_text.append(f"{portfolio.chain.upper()}\n", style="bold magenta")
    summary_text.append("Total Value:    ", style="bold cyan")
    summary_text.append(f"${total_val:,.2f} USD\n", style="bold green")
    summary_text.append("Assets Displayed: ", style="bold cyan")
    summary_text.append(f"{len(filtered)} / {len(portfolio.holdings)} total assets", style="dim")

    console.print()
    console.print(
        Panel(
            summary_text,
            title="[bold yellow]Crypto Portfolio Summary[/bold yellow]",
            border_style="cyan",
            expand=False,
        )
    )

    if not filtered:
        console.print("\n[yellow]No holdings matching filter criteria found in this wallet.[/yellow]\n")
        return

    # Holdings Table
    table = Table(
        show_header=True,
        header_style="bold blue",
        border_style="dim",
        row_styles=["none", "dim"],
    )
    table.add_column("Asset", style="bold", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Balance", justify="right", style="cyan")
    table.add_column("Price (USD)", justify="right", style="yellow")
    table.add_column("Value (USD)", justify="right", style="bold green")
    table.add_column("Share", justify="right", style="magenta")
    table.add_column("Contract / Mint", style="dim", no_wrap=True)

    for h in filtered:
        # Determine token type
        if h.is_native:
            token_type = "Native"
        elif portfolio.chain == "solana":
            token_type = "SPL"
        elif portfolio.chain == "ethereum":
            token_type = "ERC-20"
        else:
            token_type = "Token"

        # Share percentage
        if total_val > 0 and h.value_usd is not None:
            pct = (h.value_usd / total_val) * 100
            share_str = f"{pct:5.1f}%"
        else:
            share_str = "—"

        # Short address
        if h.contract_address:
            addr = h.contract_address
            short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr
        else:
            short_addr = "Native"

        table.add_row(
            h.symbol,
            h.name[:25],
            token_type,
            format_balance(h.balance),
            format_usd(h.price_usd),
            format_usd(h.value_usd),
            share_str,
            short_addr,
        )

    console.print(table)
    console.print()
