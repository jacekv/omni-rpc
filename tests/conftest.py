from collections.abc import Iterable
from typing import Any

import pytest

from omni_rpc.domain.model.chain import Chain, RpcEndpoint, VmType
from omni_rpc.domain.ports.chain_loader import ChainLoaderPort
from omni_rpc.domain.ports.logger import Logger


class NullLogger(Logger):
    """Logger that discards all messages, for use in tests."""

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        pass


class FakeChainLoader(ChainLoaderPort):
    def __init__(self, chains: list[Chain] | None = None):
        self._chains = chains or []

    def load_chains(self) -> Iterable[Chain]:
        return self._chains


def make_chain(
    key: str = "ethereum",
    chain_id: int | None = 1,
    name: str = "Ethereum",
    vm_type: VmType = VmType.EVM,
    rpcs: list[RpcEndpoint] | None = None,
) -> Chain:
    if rpcs is None:
        rpcs = [RpcEndpoint(url="https://rpc.example.com", source="upstream")]
    return Chain(key=key, chain_id=chain_id, name=name, vm_type=vm_type, rpcs=rpcs)


@pytest.fixture
def null_logger() -> NullLogger:
    return NullLogger()


@pytest.fixture
def fake_loader() -> FakeChainLoader:
    return FakeChainLoader()


@pytest.fixture
def sample_chain() -> Chain:
    return make_chain()
