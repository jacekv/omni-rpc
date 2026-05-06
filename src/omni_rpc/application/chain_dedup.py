import hashlib

from omni_rpc.domain.model.chain import Chain
from omni_rpc.domain.ports.logger import Logger


def compute_checksum(chains: list[Chain]) -> str:
    content = ",".join(
        f"{c.key}:{c.chain_id if c.chain_id is not None else ''}"
        for c in sorted(chains, key=lambda c: c.key)
    )
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def deduplicate_chains(chains: list[Chain], logger: Logger) -> list[Chain]:
    seen_keys: set[str] = set()
    seen_chain_ids: dict[int, str] = {}
    result: list[Chain] = []

    for chain in chains:
        if chain.key in seen_keys:
            logger.warning("Skipping duplicate chain key '%s'", chain.key)
            continue
        if chain.chain_id is not None and chain.chain_id in seen_chain_ids:
            logger.warning(
                "Skipping '%s': chain_id %d already claimed by '%s'",
                chain.key,
                chain.chain_id,
                seen_chain_ids[chain.chain_id],
            )
            continue
        seen_keys.add(chain.key)
        if chain.chain_id is not None:
            seen_chain_ids[chain.chain_id] = chain.key
        result.append(chain)

    return result
