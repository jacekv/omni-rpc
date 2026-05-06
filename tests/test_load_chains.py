import pytest

from omni_rpc.adapters.outbound.in_memory_chain_registry import InMemoryChainRegistry
from omni_rpc.application.load_chains import LoadChainsUseCase

from .conftest import FakeChainLoader, NullLogger, make_chain


class TestLoadChainsUseCase:
    def test_loads_and_registers_chains(self, tmp_path):
        chains = [
            make_chain(key="ethereum"),
            make_chain(key="polygon", chain_id=137, name="Polygon"),
        ]
        loader = FakeChainLoader(chains)
        registry = InMemoryChainRegistry()

        use_case = LoadChainsUseCase(
            loader=loader,
            registry=registry,
            chains_dir=tmp_path,
            logger=NullLogger(),
        )
        result = use_case.execute()

        assert len(result) == 2
        assert registry.count() == 2
        assert registry.get_by_key("ethereum") is not None
        assert registry.get_by_key("polygon") is not None

    def test_raises_when_chains_dir_missing(self, tmp_path):
        loader = FakeChainLoader([])
        registry = InMemoryChainRegistry()
        missing_dir = tmp_path / "nonexistent"

        use_case = LoadChainsUseCase(
            loader=loader,
            registry=registry,
            chains_dir=missing_dir,
            logger=NullLogger(),
        )

        with pytest.raises(RuntimeError, match="Chains data not found"):
            use_case.execute()

    def test_raises_when_no_chains_loaded(self, tmp_path):
        loader = FakeChainLoader([])
        registry = InMemoryChainRegistry()

        use_case = LoadChainsUseCase(
            loader=loader,
            registry=registry,
            chains_dir=tmp_path,
            logger=NullLogger(),
        )

        with pytest.raises(RuntimeError, match="No chains loaded"):
            use_case.execute()

    def test_duplicate_key_is_skipped(self, tmp_path):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum", chain_id=2, name="Ethereum Fork"),
        ]
        registry = InMemoryChainRegistry()
        use_case = LoadChainsUseCase(
            loader=FakeChainLoader(chains),
            registry=registry,
            chains_dir=tmp_path,
            logger=NullLogger(),
        )
        result = use_case.execute()
        assert len(result) == 1
        assert registry.count() == 1
        assert registry.get_by_key("ethereum").chain_id == 1

    def test_duplicate_chain_id_is_skipped(self, tmp_path):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum-fork", chain_id=1, name="Ethereum Fork"),
        ]
        registry = InMemoryChainRegistry()
        use_case = LoadChainsUseCase(
            loader=FakeChainLoader(chains),
            registry=registry,
            chains_dir=tmp_path,
            logger=NullLogger(),
        )
        result = use_case.execute()
        assert len(result) == 1
        assert registry.get_by_key("ethereum") is not None
        assert registry.get_by_key("ethereum-fork") is None
