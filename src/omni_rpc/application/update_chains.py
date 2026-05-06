import subprocess
from pathlib import Path

from omni_rpc.domain.ports.logger import Logger


class UpdateEthereumLists:
    def __init__(self, target_dir: Path, logger: Logger):
        self.target_dir = target_dir
        self.logger = logger

    def execute(self) -> None:
        if not self.target_dir.exists():
            raise RuntimeError(
                f"Ethereum-lists repo not found at {self.target_dir}. "
                "Run `omni-rpc init-chains` first."
            )
        self.logger.info("Pulling latest chain data from %s", self.target_dir)
        subprocess.run(
            ["git", "-C", str(self.target_dir), "pull", "--ff-only"],
            check=True,
        )
