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


def render_portfolios(
    portfolios: List[Portfolio],
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
    profile_name: Optional[str] = None,
) -> None:
    """Render one or multiple portfolios with a unified total and per-chain breakdowns."""
    if not portfolios:
        console.print("[yellow]No portfolios to display.[/yellow]")
        return

    combined_total = sum(p.total_usd for p in portfolios)
    filtered_map = {
        p.address: p.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by)
        for p in portfolios
    }

    if as_json:
        if len(portfolios) == 1:
            data = portfolios[0].to_dict()
            data["holdings"] = [h.to_dict() for h in filtered_map[portfolios[0].address]]
            print(json.dumps(data, indent=2))
        else:
            data = {
                "profile": profile_name,
                "combined_total_usd": round(combined_total, 2),
                "wallets_count": len(portfolios),
                "wallets": [
                    {
                        **p.to_dict(),
                        "holdings": [h.to_dict() for h in filtered_map[p.address]],
                    }
                    for p in portfolios
                ],
            }
            print(json.dumps(data, indent=2))
        return

    # Header Summary Panel
    summary = Text()
    if profile_name:
        summary.append("Profile:           ", style="bold cyan")
        summary.append(f"{profile_name}\n", style="bold yellow")

    for i, p in enumerate(portfolios, 1):
        summary.append(f"Wallet {i} ({p.chain.upper()}): ", style="bold cyan")
        summary.append(f"{p.address} ", style="white")
        summary.append(f"(${p.total_usd:,.2f} USD)\n", style="dim green")

    summary.append("Combined Value:    ", style="bold cyan")
    summary.append(f"${combined_total:,.2f} USD\n", style="bold green")

    total_assets = sum(len(p.holdings) for p in portfolios)
    displayed_assets = sum(len(filtered_map[p.address]) for p in portfolios)
    summary.append("Assets Displayed:  ", style="bold cyan")
    summary.append(f"{displayed_assets} / {total_assets} total assets", style="dim")

    title = f"[bold yellow]Multi-Chain Portfolio Summary[/bold yellow]"
    console.print()
    console.print(Panel(summary, title=title, border_style="cyan", expand=False))

    # Render each wallet table
    for p in portfolios:
        filtered = filtered_map[p.address]
        if filtered:
            console.print(
                _build_holdings_table(
                    p,
                    filtered,
                    f"{p.chain.upper()} Holdings ({p.address}) — ${p.total_usd:,.2f} USD",
                )
            )
            console.print()
        else:
            console.print(
                f"[dim]No active {p.chain.upper()} holdings found matching filters on {p.address}.[/dim]\n"
            )


def render_portfolio(
    portfolio: Portfolio,
    equivalent_portfolio: Optional[Portfolio] = None,
    derivation_method: Optional[str] = None,
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
) -> None:
    """Backward-compatible helper that delegates to render_portfolios."""
    portfolios = [portfolio]
    if equivalent_portfolio:
        portfolios.append(equivalent_portfolio)
    render_portfolios(
        portfolios=portfolios,
        min_usd=min_usd,
        hide_zero=hide_zero,
        sort_by=sort_by,
        as_json=as_json,
    )
