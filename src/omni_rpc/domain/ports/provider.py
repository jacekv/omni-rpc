from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResponse:
    content: bytes
    status_code: int


class ProviderError(Exception):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderNetworkError(ProviderError):
    pass


class ProviderPort(ABC):
    @abstractmethod
    async def send(self, request: bytes) -> ProviderResponse:
        pass

    @abstractmethod
    async def health(self) -> bool:
        pass
