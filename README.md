# wallet-look

A multi-chain cryptocurrency wallet portfolio tracker that inspects addresses across **Ethereum (ETH & ERC-20)**, **Solana (SOL & SPL)**, and **Bitcoin (BTC)**, displaying full asset holdings with live USD valuations.

## Features

- **Multi-Chain Support**: Auto-detects Ethereum (0x...), Solana (Base58), and Bitcoin (Legacy/SegWit/Taproot) addresses, or specify with `--chain`.
- **Full Portfolio Inspection**:
  - **Ethereum**: Native ETH balance + all ERC-20 token holdings via Ethplorer with public RPC fallback.
  - **Solana**: Native SOL balance + SPL & Token-2022 tokens via public Solana RPC.
  - **Bitcoin**: Native BTC balance via Blockstream public explorer.
- **Live USD Pricing**: Real-time USD rates and asset valuations fetched dynamically via DefiLlama and DexScreener (no paid API keys required).
- **Rich Terminal UI**: Beautiful formatted tables with balance formatting, USD values, portfolio share %, and token contracts.
- **JSON Output**: `--json` flag for scripting, pipelines, or automation.
- **Filtering & Sorting**: Filter out low-value dust (`-m / --min-value`), hide zero balances, or sort by value, balance, or symbol.

---

## Installation & Setup with UV

This project is built using [`uv`](https://github.com/astral-sh/uv).

### 1. Create Virtual Environment & Install Dependencies

```bash
# Create venv and sync dependencies
uv sync
```

Alternatively:
```bash
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## Usage

### Auto-Detect Blockchain

```bash
# Ethereum wallet (e.g. Vitalik's address)
uv run wallet-look 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045

# Solana wallet
uv run wallet-look 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM

# Bitcoin address
uv run wallet-look 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

### Filtering Low-Value Dust / Airdrops

Hide small balances or dust tokens by setting a minimum USD threshold:

```bash
# Only show holdings worth at least $50 USD
uv run wallet-look 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 -m 50
```

### JSON Output

Export clean JSON to pipe into `jq` or another tool:

```bash
uv run wallet-look 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa --json
```

### CLI Options

```text
usage: wallet-look [-h] [-c {auto,eth,ethereum,sol,solana,btc,bitcoin}]
                   [-m MIN_VALUE] [--show-zero] [-s {value,balance,symbol}]
                   [--json]
                   address

positional arguments:
  address               Public wallet address (Ethereum 0x..., Solana Base58,
                        Bitcoin 1.../3.../bc1...)

options:
  -h, --help            show this help message and exit
  -c, --chain           Target blockchain (default: auto-detect)
  -m, --min-value       Minimum USD value to display (default: 0.0)
  --show-zero           Include holdings with zero balance (default: hidden)
  -s, --sort            Sort holdings by: value (default), balance, or symbol
  --json                Output raw JSON instead of formatted terminal table
```

---

## Running Tests

Run the test suite using `pytest` via `uv`:

```bash
uv run pytest
```
