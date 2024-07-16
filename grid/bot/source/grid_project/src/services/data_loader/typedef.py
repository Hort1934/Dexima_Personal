from typing import Annotated, Literal, TypeAlias


KlineCategory: TypeAlias = Literal["linear", "inverse", "spot"]
KlineLimit: TypeAlias = Annotated[int, "Should be in range(1, 1000)"]
KlineInterval: TypeAlias = Literal[
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "12h",
    "1d",
    "1w",
    "1M",
]

LineDistribution: TypeAlias = Literal["LINEAR", "FIBONACCI"]
Sort: TypeAlias = Literal["ASCENDING", "DESCENDING"]
