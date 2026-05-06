import argparse
from dataclasses import dataclass

from omni_rpc.config.settings import Environment


@dataclass(frozen=True)
class RunArgs:
    environment: Environment


def parse_run_args() -> RunArgs:
    parser = argparse.ArgumentParser(description="OmniRPC")
    parser.add_argument(
        "--environment",
        type=Environment,
        default=Environment.DEV,
        choices=list(Environment),
        help="Configuration environment (default: dev)",
    )
    args = parser.parse_args()
    return RunArgs(environment=args.environment)
