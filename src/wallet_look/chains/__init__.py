from wallet_look.chains.base import BaseChainFetcher
from wallet_look.chains.bitcoin import BitcoinFetcher
from wallet_look.chains.ethereum import EthereumFetcher
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
    else:
        raise ValueError(f"Unsupported blockchain: {chain}")


__all__ = [
    "BaseChainFetcher",
    "EthereumFetcher",
    "SolanaFetcher",
    "BitcoinFetcher",
    "get_fetcher",
]
