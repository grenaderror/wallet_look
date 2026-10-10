from typing import Dict
from wallet_look.chains.base import BaseChainFetcher
from wallet_look.chains.bitcoin import BitcoinFetcher
from wallet_look.chains.ethereum import EthereumFetcher
from wallet_look.chains.evm_sidechain import EvmSidechainFetcher, SIDECHAIN_CONFIGS
from wallet_look.chains.hyperliquid import HyperliquidFetcher
from wallet_look.chains.solana import SolanaFetcher
from wallet_look.models import ChainType


def get_fetcher(chain: ChainType | str) -> BaseChainFetcher:
    """Return the appropriate fetcher instance for the given chain."""
    normalized = str(chain).lower().replace("chaintype.", "")

    if normalized in ("ethereum", "eth"):
        return EthereumFetcher()
    elif normalized in ("solana", "sol"):
        return SolanaFetcher()
    elif normalized in ("bitcoin", "btc"):
        return BitcoinFetcher()
    elif normalized in ("hyperliquid", "hl"):
        return HyperliquidFetcher()
    elif normalized in ("arbitrum", "arb"):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["arbitrum"])
    elif normalized in ("base",):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["base"])
    elif normalized in ("optimism", "op"):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["optimism"])
    elif normalized in ("polygon", "matic"):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["polygon"])
    elif normalized in ("bsc", "bnb"):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["bsc"])
    elif normalized in ("avalanche", "avax"):
        return EvmSidechainFetcher(SIDECHAIN_CONFIGS["avalanche"])
    else:
        raise ValueError(f"Unsupported blockchain: {chain}")


__all__ = [
    "BaseChainFetcher",
    "EthereumFetcher",
    "SolanaFetcher",
    "BitcoinFetcher",
    "HyperliquidFetcher",
    "EvmSidechainFetcher",
    "SIDECHAIN_CONFIGS",
    "get_fetcher",
]
