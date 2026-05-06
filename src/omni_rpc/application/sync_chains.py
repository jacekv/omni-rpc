from omni_rpc.application.chain_dedup import compute_checksum, deduplicate_chains
from omni_rpc.domain.ports.chain_registry import ChainRegistryPort
from omni_rpc.domain.ports.logger import Logger


class SyncChainsUseCase:
    def __init__(self, updater, loader, registry: ChainRegistryPort, logger: Logger):
        self.updater = updater
        self.loader = loader
        self.registry = registry
        self.logger = logger

    def execute(self) -> int:
        self.updater.execute()
        chains = deduplicate_chains(list(self.loader.load_chains()), self.logger)
        self.registry.reload(chains)
        self.logger.info(
            "Chain sync complete, loaded %d chains (checksum: %s)",
            len(chains),
            compute_checksum(chains),
        )
        return len(chains)
