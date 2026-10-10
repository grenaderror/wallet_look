# wallet-look

A multi-chain cryptocurrency wallet portfolio tracker that inspects addresses across **Ethereum**, **Solana**, **Bitcoin**, **TRON**, **SUI**, **EVM Sidechains/L2s** (Arbitrum, Base, Optimism, Polygon, BSC, Avalanche), and **Hyperliquid / HyperEVM**, displaying full asset holdings with live USD valuations.

## Features

- **Multi-Chain Portfolio Tracking**: Inspect multiple wallet addresses simultaneously (e.g. your Solana, Ethereum, TRON, and SUI addresses).
- **EVM Sidechains & L2s Auto-Scan**: Concurrently queries **Arbitrum**, **Base**, **Optimism**, **Polygon**, **BNB Smart Chain (BSC)**, **Avalanche C-Chain**, and **HyperEVM** for native and ERC-20 token holdings.
- **Hyperliquid L1**: Fetches spot token balances (USDC, HYPE, PURR, etc.) and perpetuals account margin equity & open positions via Hyperliquid's official Info API.
- **TRON Network**: Queries native TRX (SUN) and TRC-20 tokens (USDT, USDC, USDD, JST, BTT, etc.) via TronGrid API.
- **SUI Network**: Queries native SUI (MIST) and all Sui coin holdings via the official Sui GraphQL endpoint.
- **Wallet Profiles**: Save your addresses into named profiles (`--save <name>`) and load them anytime (`--profile <name>`).
- **Full Portfolio Inspection**:
  - **Ethereum**: Native ETH balance + all ERC-20 token holdings via Ethplorer with public RPC fallback.
  - **Solana**: Native SOL balance + SPL & Token-2022 tokens via public Solana RPC.
  - **Bitcoin**: Native BTC balance via Blockstream public explorer.
  - **TRON**: Native TRX + TRC-20 token balances via TronGrid.
  - **SUI**: Native SUI + Sui Move coins via Sui GraphQL API.
- **Cross-Chain Derivations**: For single address lookups, automatically inspects SVM/EVM equivalent addresses (Neon EVM Keccak-256 or ENS records).
- **Live USD Pricing**: Real-time USD rates and asset valuations fetched dynamically via DefiLlama, DexScreener, and Hyperliquid (no paid API keys required).
- **Rich Terminal UI**: Beautiful formatted tables with balance formatting, USD values, portfolio share %, and token contracts.
- **Single Table View**: Consolidate all holdings across multiple chains and wallets into a single unified table (`--single-table` / `--single`).
- **JSON Output**: `--json` flag for scripting, pipelines, or automation.
- **Filtering & Sorting**: Filter out low-value dust (`-m / --min-value`), hide zero balances, or sort by value, balance, or symbol.

---

## Supported Blockchains & Networks

| Network | Identifiers / Flags | Features Supported |
| :--- | :--- | :--- |
| **Ethereum** | `eth`, `ethereum` | Native ETH + All ERC-20 Tokens (Ethplorer + RPC) |
| **Solana** | `sol`, `solana` | Native SOL + SPL Tokens + Token-2022 |
| **Bitcoin** | `btc`, `bitcoin` | Native BTC (Blockstream Explorer) |
| **TRON** | `tron`, `trx` | Native TRX + TRC-20 Tokens (TronGrid API) |
| **SUI** | `sui` | Native SUI + Sui Move Coins (Sui GraphQL API) |
| **Hyperliquid** | `hl`, `hyperliquid` | Spot Tokens + Perps Margin Equity & Positions |
| **HyperEVM** | `hyperevm`, `hevm` | Native HYPE Gas + ERC-20 Tokens (USDC, PURR) |
| **Base** | `base` | Native ETH + Major Tokens (USDC, AERO, WETH) |
| **Arbitrum One** | `arb`, `arbitrum` | Native ETH + Major Tokens (USDC, USDT, ARB, WETH) |
| **OP Mainnet** | `op`, `optimism` | Native ETH + Major Tokens (USDC, USDT, OP, WETH) |
| **Polygon PoS** | `polygon`, `matic` | Native POL + Major Tokens (USDC, USDT, WETH) |
| **BNB Smart Chain**| `bsc`, `bnb` | Native BNB + Major BEP-20 Tokens (USDT, USDC, WBNB) |
| **Avalanche** | `avax`, `avalanche` | Native AVAX + Major Tokens (USDC, USDT, WAVAX) |

---

## Installation & Setup with UV

This project is built using [`uv`](https://github.com/astral-sh/uv).

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

### 1. Auto-Scan Ethereum + EVM Sidechains + Hyperliquid

When given an Ethereum (`0x...`) address, `wallet-look` automatically scans Ethereum, sidechains, and Hyperliquid concurrently:

```bash
uv run wallet-look 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 -m 100
```

### 2. Inspect Hyperliquid Directly

```bash
uv run wallet-look <EVM_ADDRESS> -c hyperliquid
# or short alias:
uv run wallet-look <EVM_ADDRESS> -c hl
```

### 3. Inspect a Specific EVM Sidechain

```bash
uv run wallet-look <EVM_ADDRESS> -c base
uv run wallet-look <EVM_ADDRESS> -c arb
uv run wallet-look <EVM_ADDRESS> -c polygon
```

### 4. Multi-Chain Wallet Lookups (SOL + ETH)

Pass both addresses directly to see a unified portfolio:

```bash
uv run wallet-look <SOL_ADDRESS> <ETH_ADDRESS> -m 50
```

### 5. Save and Load Wallet Profiles & Cost Basis

Save your addresses once so you don't have to copy-paste them every time, and optionally save purchase cost basis to track profit & loss:

```bash
# Save to a named profile (e.g. 'main')
uv run wallet-look <SOL_ADDRESS> <ETH_ADDRESS> --save main

# Save cost basis into a profile
uv run wallet-look --profile main --set-cost "ETH:2500,SOL:140"

# Load anytime with PnL automatically calculated
uv run wallet-look --profile main -m 50

# List saved profiles (including stored cost basis)
uv run wallet-look --list-profiles
```

### 6. PnL & Cost Basis Tracking

Track Profit & Loss (PnL), invested cost, and return-on-investment (ROI %):

```bash
# Ad-hoc cost basis for single lookups
uv run wallet-look <ETH_ADDRESS> --cost "ETH:2400,PEPE:0.000012"

# Automatically infer cost basis by analyzing historical stablecoin buys (USDC, USDT, DAI)
uv run wallet-look <ETH_ADDRESS> --infer-cost-basis

# Infer and automatically save to a named profile
uv run wallet-look --profile main --infer-cost-basis --save-inferred

# Sort holdings by PnL descending
uv run wallet-look --profile main -s pnl
```

> **Note on Hyperliquid**: Active perpetual positions on Hyperliquid automatically display entry price, position value, and unrealized PnL out of the box without requiring manual cost basis entry!

### 7. Inspect TRON and SUI Wallets

Auto-detection works automatically:
```bash
# TRON wallet (TRX + TRC-20 tokens like USDT, USDC, USDD)
uv run wallet-look <TRON_ADDRESS> -m 10

# SUI wallet (SUI + Sui Move coins)
uv run wallet-look <SUI_ADDRESS>
```

### 8. JSON Output

```bash
uv run wallet-look <EVM_ADDRESS> -c hl --json
```

### 9. Single Table View (Consolidate All Holdings)

Consolidate holdings across multiple chains and wallets into a single combined table:

```bash
uv run wallet-look <ETH_ADDRESS> --single-table -m 50
uv run wallet-look <SOL_ADDRESS> <ETH_ADDRESS> --single-table
```

---

## Running Tests

Run the test suite using `pytest` via `uv`:

```bash
uv run pytest
```
*Result: 44 passed.*
