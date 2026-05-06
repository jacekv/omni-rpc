from abc import ABC, abstractmethod
from collections.abc import Iterable

from omni_rpc.domain.model.chain import Chain


class ChainRegistryPort(ABC):
    @abstractmethod
    def register(self, chain: Chain) -> None:
        pass

    @abstractmethod
    def get_by_key(self, key: str) -> Chain | None:
        pass

    @abstractmethod
    def list(self) -> list[Chain]:
        pass

    @abstractmethod
    def reload(self, chains: Iterable[Chain]) -> None:
        pass
