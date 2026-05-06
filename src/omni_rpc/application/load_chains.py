from pathlib import Path

from omni_rpc.application.chain_dedup import compute_checksum, deduplicate_chains
from omni_rpc.domain.ports.logger import Logger


class LoadChainsUseCase:
    def __init__(self, loader, registry, chains_dir: Path, logger: Logger):
        self.loader = loader
        self.registry = registry
        self.chains_dir = chains_dir
        self.logger = logger

    def execute(self):
        if not self.chains_dir.exists():
            raise RuntimeError(
                f"Chains data not found at {self.chains_dir}. "
                "Run `omni-rpc init-chains` first."
            )
        self.logger.info("Loading chains from %s", self.chains_dir)

        chains = deduplicate_chains(list(self.loader.load_chains()), self.logger)

        if not chains:
            raise RuntimeError(
                f"No chains loaded from {self.chains_dir}. "
                "Data directory exists but is empty or invalid."
            )

        self.logger.info(
            "Loaded %d chains (checksum: %s)", len(chains), compute_checksum(chains)
        )

        for chain in chains:
            self.logger.debug("Registered chain: %s", chain)
            self.registry.register(chain)

        return chains
