from omni_rpc.domain.model.chain import Chain, RpcEndpoint, VmType


class TestRpcEndpoint:
    def test_creation(self):
        ep = RpcEndpoint(url="https://rpc.example.com", source="upstream")
        assert ep.url == "https://rpc.example.com"
        assert ep.source == "upstream"

    def test_frozen(self):
        ep = RpcEndpoint(url="https://rpc.example.com", source="upstream")
        try:
            ep.url = "https://other.com"
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass


class TestChain:
    def test_creation(self):
        rpcs = [RpcEndpoint(url="https://rpc.example.com", source="upstream")]
        chain = Chain(
            key="ethereum",
            chain_id=1,
            name="Ethereum",
            vm_type=VmType.EVM,
            rpcs=rpcs,
        )
        assert chain.key == "ethereum"
        assert chain.chain_id == 1
        assert chain.name == "Ethereum"
        assert chain.vm_type == VmType.EVM
        assert len(chain.rpcs) == 1

    def test_chain_id_none_for_non_evm(self):
        chain = Chain(
            key="solana",
            chain_id=None,
            name="Solana",
            vm_type=VmType.SVM,
            rpcs=[],
        )
        assert chain.chain_id is None

    def test_frozen(self):
        chain = Chain(
            key="ethereum",
            chain_id=1,
            name="Ethereum",
            vm_type=VmType.EVM,
            rpcs=[],
        )
        try:
            chain.key = "other"
            assert False, "Should raise FrozenInstanceError"
        except AttributeError:
            pass


class TestVmType:
    def test_all_values(self):
        assert VmType.EVM == "evm"
        assert VmType.SVM == "svm"
        assert VmType.SATOSHI == "satoshi"
        assert VmType.SUBSTRATE == "substrate"
        assert VmType.MOVEVM == "movevm"
