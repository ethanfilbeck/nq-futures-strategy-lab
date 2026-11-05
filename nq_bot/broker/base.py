"""Broker interface shared by the simulator and real adapters.

Rule: the engine only believes a position exists after a Fill comes back from the broker.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class BracketRequest:
    client_id: str
    side: int          # +1 buy / -1 sell
    qty: int
    stop: float
    target: float
    limit_offset_ticks: int = 4  # marketable-limit protection for entry on real brokers


@dataclass
class Fill:
    client_id: str
    kind: str          # entry | stop | target | reduce | flatten
    side: int          # +1 bought, -1 sold
    qty: int
    price: float
    ts: object


@dataclass
class OrderEvent:
    client_id: str
    status: str        # submitted | rejected | cancelled | partial
    message: str = ""


class Broker(ABC):
    @abstractmethod
    def submit_bracket(self, req: BracketRequest, ref_price: float) -> None: ...

    @abstractmethod
    def reduce(self, qty: int, client_id: str) -> None:
        """Market order closing `qty` of the current position."""

    @abstractmethod
    def modify_protection(self, stop: float, qty: int) -> None:
        """Move the protective stop and resize stop/target to `qty`."""

    @abstractmethod
    def flatten(self, reason: str) -> None:
        """Cancel all working orders and close any position at market."""

    @abstractmethod
    def position(self) -> int: ...

    @abstractmethod
    def has_working_entry(self) -> bool: ...

    @abstractmethod
    def poll(self) -> tuple[list[Fill], list[OrderEvent]]: ...

    @abstractmethod
    def is_connected(self) -> bool: ...
