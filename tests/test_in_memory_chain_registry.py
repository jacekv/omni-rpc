import pytest

from omni_rpc.adapters.outbound.in_memory_chain_registry import InMemoryChainRegistry

from .conftest import make_chain


class TestInMemoryChainRegistry:
    def test_register_and_get_by_key(self):
        registry = InMemoryChainRegistry()
        chain = make_chain(key="ethereum")
        registry.register(chain)
        assert registry.get_by_key("ethereum") == chain

    def test_get_by_key_returns_none_for_missing(self):
        registry = InMemoryChainRegistry()
        assert registry.get_by_key("nonexistent") is None

    def test_list_empty(self):
        registry = InMemoryChainRegistry()
        assert registry.list() == []

    def test_list_returns_all_registered(self):
        registry = InMemoryChainRegistry()
        c1 = make_chain(key="ethereum", name="Ethereum")
        c2 = make_chain(key="polygon", name="Polygon", chain_id=137)
        registry.register(c1)
        registry.register(c2)
        assert len(registry.list()) == 2

    def test_register_duplicate_raises(self):
        registry = InMemoryChainRegistry()
        chain = make_chain(key="ethereum")
        registry.register(chain)
        with pytest.raises(ValueError, match="Chain already registered: ethereum"):
            registry.register(chain)

    def test_count(self):
        registry = InMemoryChainRegistry()
        assert registry.count() == 0
        registry.register(make_chain(key="ethereum"))
        assert registry.count() == 1
        registry.register(make_chain(key="polygon"))
        assert registry.count() == 2
