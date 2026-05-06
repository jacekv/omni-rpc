from dataclasses import dataclass
from enum import Enum


class VmType(str, Enum):
    EVM = "evm"
    SVM = "svm"
    SATOSHI = "satoshi"
    SUBSTRATE = "substrate"
    MOVEVM = "movevm"


@dataclass(frozen=True)
class RpcEndpoint:
    url: str
    source: str  # upstream | override | manual


@dataclass(frozen=True)
class Chain:
    key: str  # "ethereum", "solana"
    chain_id: int | None  # None for non‑EVM
    name: str
    vm_type: VmType
    rpcs: list[RpcEndpoint]
