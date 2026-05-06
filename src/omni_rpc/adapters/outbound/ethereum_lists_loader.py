import json
from collections.abc import Iterable
from pathlib import Path

from omni_rpc.domain.model.chain import Chain, RpcEndpoint, VmType
from omni_rpc.domain.ports.chain_loader import ChainLoaderPort
from omni_rpc.domain.ports.logger import Logger


def _validate(data: object) -> str | None:
    """Return an error message if data fails schema validation, else None."""
    if not isinstance(data, dict):
        return "root must be a JSON object"
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return "missing or empty 'name'"
    chain_id = data.get("chainId")
    if chain_id is not None and not isinstance(chain_id, int):
        return f"'chainId' must be an integer, got {type(chain_id).__name__}"
    if not isinstance(data.get("rpc", []), list):
        return "'rpc' must be a list"
    return None


class EthereumListsChainLoader(ChainLoaderPort):
    def __init__(self, chains_dir: Path, logger: Logger):
        self._chains_dir = chains_dir
        self._logger = logger

    def load_chains(self) -> Iterable[Chain]:
        for path in self._chains_dir.glob("*.json"):
            self._logger.debug("Reading chain file: %s", path)
            try:
                with path.open() as f:
                    data = json.load(f)
            except json.JSONDecodeError as exc:
                self._logger.warning("Skipping %s: invalid JSON — %s", path.name, exc)
                continue

            error = _validate(data)
            if error:
                self._logger.warning("Skipping %s: %s", path.name, error)
                continue

            rpcs = [
                RpcEndpoint(url=url, source="upstream")
                for url in data.get("rpc", [])
                if url.startswith("https://") and "${" not in url
            ]
            if not rpcs:
                self._logger.debug(
                    "Chain '%s' has no public RPC endpoints", data["name"]
                )

            yield Chain(
                key=data["name"].lower().replace(" ", "-"),
                chain_id=data.get("chainId"),
                name=data["name"],
                vm_type=VmType.EVM,
                rpcs=rpcs,
            )
