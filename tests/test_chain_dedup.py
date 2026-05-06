from omni_rpc.application.chain_dedup import compute_checksum, deduplicate_chains

from .conftest import NullLogger, make_chain


class TestDeduplicateChains:
    def test_no_duplicates_passes_all_through(self):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="polygon", chain_id=137, name="Polygon"),
        ]
        result = deduplicate_chains(chains, NullLogger())
        assert len(result) == 2

    def test_duplicate_key_skips_second(self):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum", chain_id=2, name="Ethereum Fork"),
        ]
        result = deduplicate_chains(chains, NullLogger())
        assert len(result) == 1
        assert result[0].chain_id == 1

    def test_duplicate_chain_id_skips_second(self):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum-fork", chain_id=1, name="Ethereum Fork"),
        ]
        result = deduplicate_chains(chains, NullLogger())
        assert len(result) == 1
        assert result[0].key == "ethereum"

    def test_none_chain_id_not_deduplicated(self):
        chains = [
            make_chain(key="solana", chain_id=None, name="Solana"),
            make_chain(key="bitcoin", chain_id=None, name="Bitcoin"),
        ]
        result = deduplicate_chains(chains, NullLogger())
        assert len(result) == 2

    def test_duplicate_key_logs_warning(self):
        warnings: list[str] = []

        class CapturingLogger(NullLogger):
            def warning(self, msg, *args, **kwargs):
                warnings.append(msg % args if args else msg)

        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum", chain_id=2, name="Ethereum Fork"),
        ]
        deduplicate_chains(chains, CapturingLogger())
        assert any("ethereum" in w for w in warnings)

    def test_duplicate_chain_id_logs_warning(self):
        warnings: list[str] = []

        class CapturingLogger(NullLogger):
            def warning(self, msg, *args, **kwargs):
                warnings.append(msg % args if args else msg)

        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="ethereum-fork", chain_id=1, name="Ethereum Fork"),
        ]
        deduplicate_chains(chains, CapturingLogger())
        assert any("1" in w for w in warnings)


class TestComputeChecksum:
    def test_returns_12_char_hex_string(self):
        chains = [make_chain(key="ethereum", chain_id=1)]
        result = compute_checksum(chains)
        assert len(result) == 12
        assert all(c in "0123456789abcdef" for c in result)

    def test_same_chains_same_checksum(self):
        chains = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="polygon", chain_id=137, name="Polygon"),
        ]
        assert compute_checksum(chains) == compute_checksum(chains)

    def test_order_independent(self):
        a = [
            make_chain(key="ethereum", chain_id=1),
            make_chain(key="polygon", chain_id=137, name="Polygon"),
        ]
        b = [
            make_chain(key="polygon", chain_id=137, name="Polygon"),
            make_chain(key="ethereum", chain_id=1),
        ]
        assert compute_checksum(a) == compute_checksum(b)

    def test_different_chains_different_checksum(self):
        a = [make_chain(key="ethereum", chain_id=1)]
        b = [make_chain(key="polygon", chain_id=137, name="Polygon")]
        assert compute_checksum(a) != compute_checksum(b)

    def test_empty_list(self):
        assert len(compute_checksum([])) == 12


class TestDeduplicateChainOrder:
    def test_preserves_order_of_first_occurrences(self):
        chains = [
            make_chain(key="a", chain_id=1, name="A"),
            make_chain(key="b", chain_id=2, name="B"),
            make_chain(key="a", chain_id=3, name="A Dup"),
            make_chain(key="c", chain_id=4, name="C"),
        ]
        result = deduplicate_chains(chains, NullLogger())
        assert [c.key for c in result] == ["a", "b", "c"]
