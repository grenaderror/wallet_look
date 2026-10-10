# wallet-look

A multi-chain cryptocurrency wallet portfolio tracker that inspects addresses across **Ethereum (ETH & ERC-20)**, **Solana (SOL & SPL)**, and **Bitcoin (BTC)**, displaying full asset holdings with live USD valuations.

## Features

- **Multi-Chain Portfolio Tracking**: Inspect multiple wallet addresses simultaneously (e.g. your Solana and Ethereum addresses from Phantom, Backpack, or Ledger).
- **Wallet Profiles**: Save your addresses into named profiles (`--save <name>`) and load them anytime (`--profile <name>`).
- **Full Portfolio Inspection**:
  - **Ethereum**: Native ETH balance + all ERC-20 token holdings via Ethplorer with public RPC fallback.
  - **Solana**: Native SOL balance + SPL & Token-2022 tokens via public Solana RPC.
  - **Bitcoin**: Native BTC balance via Blockstream public explorer.
- **Cross-Chain Derivations**: For single address lookups, automatically inspects SVM/EVM equivalent addresses (Neon EVM Keccak-256 or ENS records).
- **Live USD Pricing**: Real-time USD rates and asset valuations fetched dynamically via DefiLlama and DexScreener (no paid API keys required).
- **Rich Terminal UI**: Beautiful formatted tables with balance formatting, USD values, portfolio share %, and token contracts.
- **JSON Output**: `--json` flag for scripting, pipelines, or automation.
- **Filtering & Sorting**: Filter out low-value dust (`-m / --min-value`), hide zero balances, or sort by value, balance, or symbol.

---

## Why Phantom/Wallet App ETH & SOL Addresses Differ

Multi-chain wallets like Phantom, Backpack, and Solflare derive their accounts from the **same secret seed phrase** (mnemonic), but use distinct cryptographic curves and derivation paths:
- **Ethereum**: `m/44'/60'/0'/0/0` via **secp256k1**
- **Solana**: `m/44'/501'/0'/0'` via **ed25519**

Because public-key cryptography and key derivation functions are one-way, **a public Solana address cannot mathematically derive the wallet's Ethereum address without the secret seed phrase**.

To track your wallet across both chains, you can pass both addresses together or save them to a profile.

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

### 1. Multi-Chain Wallet Lookups (SOL + ETH)

Pass both addresses directly to see a unified portfolio:

```bash
uv run wallet-look <SOL_ADDRESS> <ETH_ADDRESS> -m 100
```

### 2. Save and Load Wallet Profiles

Save your addresses once so you don't have to copy-paste them every time:

```bash
# Save to a named profile (e.g. 'phantom')
uv run wallet-look <SOL_ADDRESS> <ETH_ADDRESS> --save phantom

# Load anytime
uv run wallet-look --profile phantom -m 50

# List saved profiles
uv run wallet-look --list-profiles
```

### 3. Single Address Auto-Detection

```bash
# Solana wallet
uv run wallet-look 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM -m 100

# Ethereum wallet
uv run wallet-look 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 -m 50

# Bitcoin address
uv run wallet-look 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

### 4. JSON Output

```bash
uv run wallet-look --profile phantom --json
```

### CLI Options

```text
usage: wallet-look [-h] [--eth ETH] [--sol SOL] [--btc BTC]
                   [-p PROFILE] [--save PROFILE_NAME] [--list-profiles]
                   [-c {auto,eth,ethereum,sol,solana,btc,bitcoin}]
                   [-m MIN_VALUE] [--show-zero] [--no-equivalent]
                   [-s {value,balance,symbol}] [--json]
                   [addresses ...]

positional arguments:
  addresses             One or more wallet addresses (e.g. SOL address and ETH address)

options:
  -h, --help            show this help message and exit
  --eth ETH             Explicit Ethereum address to include
  --sol SOL             Explicit Solana address to include
  --btc BTC             Explicit Bitcoin address to include
  -p, --profile         Load saved wallet profile by name (e.g. --profile phantom)
  --save PROFILE_NAME   Save provided addresses to a named profile
  --list-profiles       List all saved wallet profiles and exit
  -c, --chain           Target blockchain (default: auto-detect)
  -m, --min-value       Minimum USD value to display (default: 0.0)
  --show-zero           Include holdings with zero balance (default: hidden)
  --no-equivalent       Disable automatic cross-chain equivalent address fallback
  -s, --sort            Sort holdings by: value (default), balance, or symbol
  --json                Output raw JSON instead of formatted terminal table
```

---

## Running Tests

Run the test suite using `pytest` via `uv`:

```bash
uv run pytest
```
