"""
This describes the use of the named tupple class
"""

from decimal import Decimal
from typing import NamedTuple


class Stock(NamedTuple):
    symbol: str
    current: Decimal
    high: Decimal
    low: Decimal
