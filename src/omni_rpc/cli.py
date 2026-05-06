from pathlib import Path

import typer

from omni_rpc.application.bootstrap_chains import BootstrapEthereumLists

app = typer.Typer()


@app.command()
def init_chains():
    """
    Download the ethereum-lists/chains repository.
    Must be run before starting the API.
    """
    BootstrapEthereumLists(target_dir=Path("data/ethereum-lists")).execute()

    typer.echo("✅ Ethereum chains data initialized")


@app.command()
def version():
    typer.echo("0.1.0")
