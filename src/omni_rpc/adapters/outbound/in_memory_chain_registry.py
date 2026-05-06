from collections.abc import Iterable

from omni_rpc.domain.model.chain import Chain
from omni_rpc.domain.ports.chain_registry import ChainRegistryPort


class InMemoryChainRegistry(ChainRegistryPort):
    def __init__(self):
        self._chains: dict[str, Chain] = {}

    def register(self, chain: Chain) -> None:
        if chain.key in self._chains:
            raise ValueError(f"Chain already registered: {chain.key}")
        self._chains[chain.key] = chain

    def get_by_key(self, key: str) -> Chain | None:
        return self._chains.get(key)

    def list(self) -> list[Chain]:
        return list(self._chains.values())

    def reload(self, chains: Iterable[Chain]) -> None:
        self._chains = {chain.key: chain for chain in chains}

    def count(self) -> int:
        return len(self._chains)
