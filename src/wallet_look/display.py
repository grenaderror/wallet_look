from __future__ import annotations

import json
from typing import List, Optional
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


def _build_holdings_table(
    portfolio: Portfolio,
    filtered: List[Holding],
    table_title: str,
) -> Table:
    table = Table(
        title=table_title,
        title_style="bold yellow",
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

    total_val = portfolio.total_usd
    for h in filtered:
        if h.is_native:
            token_type = "Native"
        elif portfolio.chain == "solana":
            token_type = "SPL"
        elif portfolio.chain == "ethereum":
            token_type = "ERC-20"
        else:
            token_type = "Token"

        if total_val > 0 and h.value_usd is not None:
            pct = (h.value_usd / total_val) * 100
            share_str = f"{pct:5.1f}%"
        else:
            share_str = "—"

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
    return table


def render_portfolio(
    portfolio: Portfolio,
    equivalent_portfolio: Optional[Portfolio] = None,
    derivation_method: Optional[str] = None,
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
) -> None:
    """Render the portfolio and optional cross-chain equivalent portfolio."""
    filtered_primary = portfolio.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by)
    combined_total = portfolio.total_usd

    filtered_eq: List[Holding] = []
    if equivalent_portfolio:
        filtered_eq = equivalent_portfolio.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by)
        combined_total += equivalent_portfolio.total_usd

    if as_json:
        data = portfolio.to_dict()
        data["holdings"] = [h.to_dict() for h in filtered_primary]
        if equivalent_portfolio:
            eq_data = equivalent_portfolio.to_dict()
            eq_data["derivation_method"] = derivation_method
            eq_data["holdings"] = [h.to_dict() for h in filtered_eq]
            data["equivalent"] = eq_data
            data["combined_total_usd"] = round(combined_total, 2)
        print(json.dumps(data, indent=2))
        return

    # Header Panel
    summary_text = Text()
    summary_text.append("Primary Wallet:    ", style="bold cyan")
    summary_text.append(f"{portfolio.address} ", style="white")
    summary_text.append(f"[{portfolio.chain.upper()}]\n", style="bold magenta")

    if equivalent_portfolio:
        summary_text.append("Equivalent Wallet: ", style="bold cyan")
        summary_text.append(f"{equivalent_portfolio.address} ", style="white")
        summary_text.append(f"[{equivalent_portfolio.chain.upper()}]\n", style="bold magenta")
        if derivation_method:
            summary_text.append("Mapping Method:    ", style="bold cyan")
            summary_text.append(f"{derivation_method}\n", style="dim yellow")

    summary_text.append("Combined Value:    ", style="bold cyan")
    summary_text.append(f"${combined_total:,.2f} USD\n", style="bold green")

    summary_text.append("Assets Displayed:  ", style="bold cyan")
    total_assets = len(portfolio.holdings) + (len(equivalent_portfolio.holdings) if equivalent_portfolio else 0)
    displayed_assets = len(filtered_primary) + len(filtered_eq)
    summary_text.append(f"{displayed_assets} / {total_assets} total assets", style="dim")

    console.print()
    console.print(
        Panel(
            summary_text,
            title="[bold yellow]Multi-Chain Portfolio Summary[/bold yellow]",
            border_style="cyan",
            expand=False,
        )
    )

    # 1. Primary Holdings Table
    if filtered_primary:
        console.print(
            _build_holdings_table(
                portfolio,
                filtered_primary,
                f"{portfolio.chain.upper()} Holdings ({portfolio.address})",
            )
        )
        console.print()
    else:
        console.print(f"[yellow]No {portfolio.chain.upper()} holdings matching filter criteria found.[/yellow]\n")

    # 2. Equivalent Chain Holdings Table
    if equivalent_portfolio:
        if filtered_eq:
            console.print(
                _build_holdings_table(
                    equivalent_portfolio,
                    filtered_eq,
                    f"Equivalent {equivalent_portfolio.chain.upper()} Holdings ({equivalent_portfolio.address})",
                )
            )
            console.print()
        else:
            console.print(
                f"[dim]No active {equivalent_portfolio.chain.upper()} holdings found on equivalent address "
                f"({equivalent_portfolio.address}).[/dim]\n"
            )
