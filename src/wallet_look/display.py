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


def format_pnl(val: float | None, is_pct: bool = False) -> str:
    """Format PnL with green for positive, red for negative, and dim for N/A."""
    if val is None:
        return "[dim]—[/dim]"
    if abs(val) < 0.000001:
        return "$0.00" if not is_pct else "0.0%"
    color = "green" if val > 0 else "red"
    prefix = "+" if val > 0 else "-"
    abs_val = abs(val)
    if is_pct:
        return f"[{color}]{prefix}{abs_val:.1f}%[/{color}]"
    if abs_val < 0.01:
        return f"[{color}]{prefix}${abs_val:.6f}[/{color}]"
    return f"[{color}]{prefix}${abs_val:,.2f}[/{color}]"


CHAIN_DISPLAY_NAMES = {
    "ethereum": "Ethereum",
    "eth": "Ethereum",
    "solana": "Solana",
    "sol": "Solana",
    "bitcoin": "Bitcoin",
    "btc": "Bitcoin",
    "arbitrum": "Arbitrum",
    "arb": "Arbitrum",
    "base": "Base",
    "optimism": "Optimism",
    "op": "Optimism",
    "polygon": "Polygon",
    "matic": "Polygon",
    "bsc": "BSC",
    "bnb": "BSC",
    "avalanche": "Avalanche",
    "avax": "Avalanche",
    "hyperliquid": "Hyperliquid",
    "hl": "Hyperliquid",
    "hyperevm": "HyperEVM",
    "hevm": "HyperEVM",
    "tron": "TRON",
    "trx": "TRON",
    "sui": "SUI",
}


def format_chain_name(chain: str) -> str:
    """Format chain identifier into a friendly display name."""
    return CHAIN_DISPLAY_NAMES.get(chain.lower(), chain.capitalize())


def _get_token_type(h: Holding, chain: str) -> str:
    """Determine human-readable token type for an asset."""
    if h.is_native:
        return "Native"
    c = chain.lower()
    if c == "solana":
        return "SPL"
    if c in ("ethereum", "arbitrum", "base", "optimism", "polygon", "avalanche", "hyperevm"):
        return "ERC-20"
    if c == "bsc":
        return "BEP-20"
    if c == "tron":
        return "TRC-20"
    if c == "sui":
        return "Coin"
    if c == "hyperliquid":
        if "PERP" in h.symbol:
            return "Perp"
        if "Margin" in h.name:
            return "Margin"
        return "Spot"
    return "Token"


def _build_holdings_table(
    portfolio: Portfolio,
    filtered: List[Holding],
    table_title: str,
) -> Table:
    has_pnl = any(h.cost_basis is not None or h.pnl_usd is not None for h in filtered)

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
    if has_pnl:
        table.add_column("Cost Basis", justify="right", style="cyan")
        table.add_column("PnL (USD)", justify="right")
        table.add_column("ROI", justify="right")
    table.add_column("Share", justify="right", style="magenta")
    table.add_column("Contract / Mint", style="dim", no_wrap=True)

    total_val = portfolio.total_usd
    for h in filtered:
        token_type = _get_token_type(h, portfolio.chain)

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

        row = [
            h.symbol,
            h.name[:25],
            token_type,
            format_balance(h.balance),
            format_usd(h.price_usd),
            format_usd(h.value_usd),
        ]
        if has_pnl:
            cost_str = format_usd(h.cost_basis) if h.cost_basis is not None else "[dim]—[/dim]"
            pnl_str = format_pnl(h.pnl_usd)
            roi_str = format_pnl(h.pnl_pct, is_pct=True)
            row.extend([cost_str, pnl_str, roi_str])
        row.extend([share_str, short_addr])
        table.add_row(*row)
    return table


def _build_consolidated_table(
    items: List[tuple[Portfolio, Holding]],
    combined_total: float,
    table_title: str,
    show_wallet: bool = False,
) -> Table:
    has_pnl = any(h.cost_basis is not None or h.pnl_usd is not None for _, h in items)

    table = Table(
        title=table_title,
        title_style="bold yellow",
        show_header=True,
        header_style="bold blue",
        border_style="dim",
        row_styles=["none", "dim"],
    )
    table.add_column("Chain", style="bold cyan")
    if show_wallet:
        table.add_column("Wallet", style="dim", no_wrap=True)
    table.add_column("Asset", style="bold", no_wrap=True)
    table.add_column("Name", style="white")
    table.add_column("Type", style="dim")
    table.add_column("Balance", justify="right", style="cyan")
    table.add_column("Price (USD)", justify="right", style="yellow")
    table.add_column("Value (USD)", justify="right", style="bold green")
    if has_pnl:
        table.add_column("Cost Basis", justify="right", style="cyan")
        table.add_column("PnL (USD)", justify="right")
        table.add_column("ROI", justify="right")
    table.add_column("Share", justify="right", style="magenta")
    table.add_column("Contract / Mint", style="dim", no_wrap=True)

    for p, h in items:
        token_type = _get_token_type(h, p.chain)

        if combined_total > 0 and h.value_usd is not None:
            pct = (h.value_usd / combined_total) * 100
            share_str = f"{pct:5.1f}%"
        else:
            share_str = "—"

        if h.contract_address:
            addr = h.contract_address
            short_addr = f"{addr[:6]}...{addr[-4:]}" if len(addr) > 12 else addr
        else:
            short_addr = "Native"

        row = [format_chain_name(p.chain)]
        if show_wallet:
            wallet_short = f"{p.address[:6]}...{p.address[-4:]}" if len(p.address) > 12 else p.address
            row.append(wallet_short)

        row.extend([
            h.symbol,
            h.name[:25],
            token_type,
            format_balance(h.balance),
            format_usd(h.price_usd),
            format_usd(h.value_usd),
        ])
        if has_pnl:
            cost_str = format_usd(h.cost_basis) if h.cost_basis is not None else "[dim]—[/dim]"
            pnl_str = format_pnl(h.pnl_usd)
            roi_str = format_pnl(h.pnl_pct, is_pct=True)
            row.extend([cost_str, pnl_str, roi_str])
        row.extend([share_str, short_addr])
        table.add_row(*row)

    return table


def render_portfolios(
    portfolios: List[Portfolio],
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
    profile_name: Optional[str] = None,
    single_table: bool = False,
) -> None:
    """Render one or multiple portfolios with a unified total and per-chain breakdowns."""
    if not portfolios:
        console.print("[yellow]No portfolios to display.[/yellow]")
        return

    combined_total = sum(p.total_usd for p in portfolios)
    portfolio_items = [
        (p, p.filter_and_sort(min_usd=min_usd, hide_zero=hide_zero, sort_by=sort_by))
        for p in portfolios
    ]

    all_items: List[tuple[Portfolio, Holding]] = []
    for p, filtered in portfolio_items:
        for h in filtered:
            all_items.append((p, h))

    if sort_by == "value":
        all_items.sort(
            key=lambda item: (
                item[1].value_usd is not None,
                item[1].value_usd if item[1].value_usd is not None else -1.0,
                item[1].balance,
            ),
            reverse=True,
        )
    elif sort_by == "balance":
        all_items.sort(key=lambda item: item[1].balance, reverse=True)
    elif sort_by == "symbol":
        all_items.sort(key=lambda item: item[1].symbol.upper())
    elif sort_by == "pnl":
        all_items.sort(
            key=lambda item: (
                item[1].pnl_usd is not None,
                item[1].pnl_usd if item[1].pnl_usd is not None else -1e12,
            ),
            reverse=True,
        )

    costs_list = [p.total_cost_usd for p in portfolios if p.total_cost_usd is not None]
    combined_cost = sum(costs_list) if costs_list else None
    pnls_list = [p.total_pnl_usd for p in portfolios if p.total_pnl_usd is not None]
    combined_pnl = sum(pnls_list) if pnls_list else None
    has_summary_pnl = combined_cost is not None or combined_pnl is not None

    if as_json:
        if single_table:
            data = {
                "profile": profile_name,
                "combined_total_usd": round(combined_total, 2),
                "combined_cost_usd": round(combined_cost, 2) if combined_cost is not None else None,
                "combined_pnl_usd": round(combined_pnl, 2) if combined_pnl is not None else None,
                "wallets_count": len(portfolios),
                "holdings_count": len(all_items),
                "holdings": [
                    {
                        **h.to_dict(),
                        "chain": p.chain,
                        "address": p.address,
                    }
                    for p, h in all_items
                ],
            }
            print(json.dumps(data, indent=2))
        elif len(portfolios) == 1:
            p, filtered = portfolio_items[0]
            data = p.to_dict()
            data["holdings"] = [h.to_dict() for h in filtered]
            print(json.dumps(data, indent=2))
        else:
            data = {
                "profile": profile_name,
                "combined_total_usd": round(combined_total, 2),
                "combined_cost_usd": round(combined_cost, 2) if combined_cost is not None else None,
                "combined_pnl_usd": round(combined_pnl, 2) if combined_pnl is not None else None,
                "wallets_count": len(portfolios),
                "wallets": [
                    {
                        **p.to_dict(),
                        "holdings": [h.to_dict() for h in filtered],
                    }
                    for p, filtered in portfolio_items
                ],
            }
            print(json.dumps(data, indent=2))
        return

    # Header Summary Panel
    summary = Text()
    if profile_name:
        summary.append("Profile:           ", style="bold cyan")
        summary.append(f"{profile_name}\n", style="bold yellow")

    for i, (p, filtered) in enumerate(portfolio_items, 1):
        summary.append(f"Wallet {i} ({p.chain.upper()}): ", style="bold cyan")
        short_addr = f"{p.address[:8]}...{p.address[-6:]}" if len(p.address) > 20 else p.address
        summary.append(f"{short_addr} ", style="white")
        summary.append(f"(${p.total_usd:,.2f} USD)\n", style="dim green")

    summary.append("Combined Value:    ", style="bold cyan")
    summary.append(f"${combined_total:,.2f} USD\n", style="bold green")

    if has_summary_pnl:
        if combined_cost is not None and combined_cost > 0:
            summary.append("Invested Cost:     ", style="bold cyan")
            summary.append(f"${combined_cost:,.2f} USD\n", style="white")
        if combined_pnl is not None:
            roi_val = (combined_pnl / combined_cost * 100) if (combined_cost and combined_cost > 0) else 0.0
            pnl_style = "bold green" if combined_pnl >= 0 else "bold red"
            sign = "+" if combined_pnl > 0 else ""
            summary.append("Total PnL:         ", style="bold cyan")
            summary.append(f"{sign}${combined_pnl:,.2f} USD ", style=pnl_style)
            if combined_cost and combined_cost > 0:
                summary.append(f"({sign}{roi_val:.1f}%)\n", style=pnl_style)
            else:
                summary.append("\n")

    total_assets = sum(len(p.holdings) for p, _ in portfolio_items)
    displayed_assets = sum(len(filtered) for _, filtered in portfolio_items)
    summary.append("Assets Displayed:  ", style="bold cyan")
    summary.append(f"{displayed_assets} / {total_assets} total assets", style="dim")

    title = f"[bold yellow]Multi-Chain Portfolio Summary[/bold yellow]"
    console.print()
    console.print(Panel(summary, title=title, border_style="cyan", expand=False))

    if single_table:
        if all_items:
            unique_addrs = {p.address for p in portfolios if p.address}
            if profile_name:
                table_title = f"Consolidated Holdings ({profile_name}) — ${combined_total:,.2f} USD"
            elif len(unique_addrs) == 1:
                table_title = f"Consolidated Holdings ({next(iter(unique_addrs))}) — ${combined_total:,.2f} USD"
            else:
                table_title = f"Consolidated Holdings — ${combined_total:,.2f} USD"

            console.print(
                _build_consolidated_table(
                    items=all_items,
                    combined_total=combined_total,
                    table_title=table_title,
                    show_wallet=len(unique_addrs) > 1,
                )
            )
            console.print()
        elif combined_total > 0 or not hide_zero:
            console.print(
                f"[dim]No active holdings found matching filter >= ${min_usd:,.2f} USD.[/dim]\n"
            )
        return

    # Render each wallet table
    for p, filtered in portfolio_items:
        if filtered:
            console.print(
                _build_holdings_table(
                    p,
                    filtered,
                    f"{p.chain.upper()} Holdings ({p.address}) — ${p.total_usd:,.2f} USD",
                )
            )
            console.print()
        elif p.total_usd > 0 or not hide_zero:
            console.print(
                f"[dim]No active {p.chain.upper()} holdings found matching filter >= ${min_usd:,.2f} USD ({p.address}).[/dim]\n"
            )


def render_portfolio(
    portfolio: Portfolio,
    equivalent_portfolio: Optional[Portfolio] = None,
    derivation_method: Optional[str] = None,
    min_usd: float = 0.0,
    hide_zero: bool = True,
    sort_by: str = "value",
    as_json: bool = False,
    single_table: bool = False,
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
        single_table=single_table,
    )
