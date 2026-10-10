from abc import ABC, abstractmethod
from wallet_look.models import Portfolio


class BaseChainFetcher(ABC):
    """Abstract base class for blockchain portfolio fetchers."""

    @abstractmethod
    def fetch_portfolio(self, address: str) -> Portfolio:
        """Fetch full token holdings and USD valuations for the given address."""
        pass
