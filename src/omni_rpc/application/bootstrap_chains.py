import subprocess
from pathlib import Path

ETHEREUM_LISTS_REPO = "https://github.com/ethereum-lists/chains.git"


class BootstrapEthereumLists:
    def __init__(self, target_dir: Path):
        self.target_dir = target_dir

    def execute(self) -> None:
        if self.target_dir.exists():
            return

        self.target_dir.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            ["git", "clone", "--depth", "1", ETHEREUM_LISTS_REPO, str(self.target_dir)],
            check=True,
        )
