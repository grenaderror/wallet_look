from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ChainType(str, Enum):
    ETHEREUM = "ethereum"
    SOLANA = "solana"
    BITCOIN = "bitcoin"


@dataclass
class Holding:
    symbol: str
    name: str
    balance: float
    decimals: int = 18
    contract_address: Optional[str] = None
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None
    is_native: bool = False
    chain: str = "ethereum"

    def __post_init__(self) -> None:
        if self.price_usd is not None and self.value_usd is None:
            self.value_usd = round(self.balance * self.price_usd, 6)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "balance": self.balance,
            "decimals": self.decimals,
            "contract_address": self.contract_address,
            "price_usd": self.price_usd,
            "value_usd": self.value_usd,
            "is_native": self.is_native,
            "chain": self.chain,
        }


@dataclass
class Portfolio:
    address: str
    chain: str
    holdings: List[Holding] = field(default_factory=list)

    @property
    def total_usd(self) -> float:
        return sum(h.value_usd for h in self.holdings if h.value_usd is not None)

    @property
    def priced_count(self) -> int:
        return sum(1 for h in self.holdings if h.value_usd is not None)

    @property
    def unpriced_count(self) -> int:
        return sum(1 for h in self.holdings if h.value_usd is None)

    def filter_and_sort(
        self,
        min_usd: float = 0.0,
        hide_zero: bool = True,
        sort_by: str = "value",
    ) -> List[Holding]:
        filtered: List[Holding] = []
        for h in self.holdings:
            if hide_zero and h.balance <= 0:
                continue
            val = h.value_usd if h.value_usd is not None else 0.0
            if val < min_usd:
                continue
            filtered.append(h)

        if sort_by == "value":
            filtered.sort(
                key=lambda x: (
                    x.value_usd is not None,
                    x.value_usd if x.value_usd is not None else -1.0,
                    x.balance,
                ),
                reverse=True,
            )
        elif sort_by == "balance":
            filtered.sort(key=lambda x: x.balance, reverse=True)
        elif sort_by == "symbol":
            filtered.sort(key=lambda x: x.symbol.upper())

        return filtered

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "chain": self.chain,
            "total_usd": round(self.total_usd, 2),
            "holdings_count": len(self.holdings),
            "holdings": [h.to_dict() for h in self.holdings],
        }
