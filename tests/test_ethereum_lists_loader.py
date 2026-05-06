import json

from omni_rpc.adapters.outbound.ethereum_lists_loader import EthereumListsChainLoader
from omni_rpc.domain.model.chain import VmType

from .conftest import NullLogger


class TestEthereumListsChainLoader:
    def test_loads_chain_from_json(self, tmp_path):
        chain_data = {
            "name": "Ethereum",
            "chainId": 1,
            "rpc": [
                "https://mainnet.infura.io/v3/key",
                "https://eth.llamarpc.com",
            ],
        }
        (tmp_path / "eip155-1.json").write_text(json.dumps(chain_data))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert len(chains) == 1
        chain = chains[0]
        assert chain.key == "ethereum"
        assert chain.chain_id == 1
        assert chain.name == "Ethereum"
        assert chain.vm_type == VmType.EVM
        assert len(chain.rpcs) == 2
        assert all(r.source == "upstream" for r in chain.rpcs)

    def test_filters_non_https_rpcs(self, tmp_path):
        chain_data = {
            "name": "Test Chain",
            "chainId": 99,
            "rpc": [
                "https://good.example.com",
                "http://insecure.example.com",
                "wss://websocket.example.com",
            ],
        }
        (tmp_path / "eip155-99.json").write_text(json.dumps(chain_data))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert len(chains[0].rpcs) == 1
        assert chains[0].rpcs[0].url == "https://good.example.com"

    def test_filters_template_rpcs(self, tmp_path):
        chain_data = {
            "name": "Test Chain",
            "chainId": 99,
            "rpc": [
                "https://mainnet.infura.io/v3/${INFURA_API_KEY}",
                "https://plain.example.com",
            ],
        }
        (tmp_path / "eip155-99.json").write_text(json.dumps(chain_data))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert len(chains[0].rpcs) == 1
        assert chains[0].rpcs[0].url == "https://plain.example.com"

    def test_name_to_kebab_case_key(self, tmp_path):
        chain_data = {
            "name": "BNB Smart Chain",
            "chainId": 56,
            "rpc": [],
        }
        (tmp_path / "eip155-56.json").write_text(json.dumps(chain_data))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert chains[0].key == "bnb-smart-chain"

    def test_empty_directory(self, tmp_path):
        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())
        assert chains == []

    def test_chain_without_rpc_field(self, tmp_path):
        chain_data = {"name": "No RPC Chain", "chainId": 999}
        (tmp_path / "eip155-999.json").write_text(json.dumps(chain_data))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert len(chains) == 1
        assert chains[0].rpcs == []

    def test_skips_invalid_json_file(self, tmp_path):
        (tmp_path / "bad.json").write_text("not json {{{")
        (tmp_path / "eip155-1.json").write_text(
            json.dumps({"name": "Ethereum", "chainId": 1, "rpc": []})
        )

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert len(chains) == 1
        assert chains[0].key == "ethereum"

    def test_skips_file_missing_name(self, tmp_path):
        (tmp_path / "no-name.json").write_text(json.dumps({"chainId": 1, "rpc": []}))

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert chains == []

    def test_skips_file_with_empty_name(self, tmp_path):
        (tmp_path / "empty-name.json").write_text(
            json.dumps({"name": "  ", "chainId": 1, "rpc": []})
        )

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert chains == []

    def test_skips_file_with_non_integer_chain_id(self, tmp_path):
        (tmp_path / "bad-id.json").write_text(
            json.dumps({"name": "Bad Chain", "chainId": "not-an-int", "rpc": []})
        )

        loader = EthereumListsChainLoader(tmp_path, NullLogger())
        chains = list(loader.load_chains())

        assert chains == []

    def test_invalid_file_logs_warning(self, tmp_path):
        warnings: list[str] = []

        class CapturingLogger(NullLogger):
            def warning(self, msg, *args, **kwargs):
                warnings.append(msg % args if args else msg)

        (tmp_path / "bad.json").write_text("not json")

        loader = EthereumListsChainLoader(tmp_path, CapturingLogger())
        list(loader.load_chains())

        assert any("bad.json" in w for w in warnings)
