from abc import ABC, abstractmethod
from collections.abc import Iterable

from omni_rpc.domain.model.chain import Chain


class ChainLoaderPort(ABC):
    @abstractmethod
    def load_chains(self) -> Iterable[Chain]:
        pass
