from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


def get_config(environment: Environment) -> dict:
    config_file_path = Path(f"config/{environment.value}.yaml")
    if not config_file_path.is_file():
        raise ValueError(f"Unable to find configuration file: {config_file_path}.")
    with config_file_path.open() as f:
        return yaml.safe_load(f)


def load_settings(environment: Environment) -> "Settings":
    config = get_config(environment)
    return Settings(config)


def parse_and_load_environment_settings() -> "Settings":
    from omni_rpc.arg_parser import parse_run_args

    args = parse_run_args()
    return load_settings(args.environment)


class Settings:
    def __init__(self, config: dict):
        self._config = config

    @property
    def data_dir(self) -> Path:
        return Path(self._config.get("data_dir", "data")).resolve()

    @property
    def chains_dir(self) -> Path:
        return self.data_dir / "ethereum-lists/_data/chains"

    @property
    def rate_limit(self) -> str:
        return f"{self._config['rate_limit']}/minute"

    # --- Chains ---

    @property
    def chain_sync_interval(self) -> int:
        return self._config.get("chains", {}).get("sync_interval_seconds", 3600)

    # --- Cache ---

    _DEFAULT_CACHE_TTLS: dict[str, int] = {
        "eth_chainId": 86400,
        "net_version": 3600,
        "net_listening": 30,
        "web3_clientVersion": 3600,
        "web3_sha3": 86400,
    }

    @property
    def redis_url(self) -> str | None:
        return self._config.get("cache", {}).get("redis_url", None)

    @property
    def cache_ttls(self) -> dict[str, int]:
        overrides = self._config.get("cache", {}).get("method_ttls", {})
        return {**self._DEFAULT_CACHE_TTLS, **overrides}

    # --- RPC ---

    @property
    def allowed_method_prefixes(self) -> set[str]:
        prefixes = self._config.get("rpc", {}).get(
            "allowed_method_prefixes", ["eth", "net", "web3"]
        )
        return set(prefixes)

    @property
    def max_payload_bytes(self) -> int:
        return int(self._config.get("rpc", {}).get("max_payload_bytes", 65536))

    @property
    def request_timeout_seconds(self) -> float:
        return float(self._config.get("rpc", {}).get("request_timeout_seconds", 30.0))

    @property
    def upstream_timeout_seconds(self) -> float:
        return float(self._config.get("rpc", {}).get("upstream_timeout_seconds", 10.0))

    # --- Server ---

    @property
    def host(self) -> str:
        return self._config.get("api", {}).get("host", "127.0.0.1")

    @property
    def port(self) -> int:
        return self._config.get("api", {}).get("port", 8000)

    @property
    def workers(self) -> int:
        return self._config.get("api", {}).get("workers", 1)

    @property
    def reload(self) -> bool:
        return self._config.get("api", {}).get("reload", False)

    @property
    def access_log(self) -> bool:
        return self._config.get("api", {}).get("access_log", True)

    # --- Logging ---

    @property
    def log_formatter(self) -> str:
        return self._config.get("logging", {}).get("formatter", "standard")

    @property
    def log_handler(self) -> str:
        return self._config.get("logging", {}).get("handler", "stdout")

    @property
    def log_levels(self) -> dict:
        return self._config.get("logging", {}).get(
            "levels",
            {
                "root": "WARNING",
                "omni_rpc": "INFO",
                "uvicorn": "INFO",
            },
        )

    @property
    def log_config(self) -> dict[str, Any]:
        from omni_rpc.logging import get_log_config

        return get_log_config(self.log_formatter, self.log_handler, self.log_levels)

    def configure_logging(self) -> None:
        from omni_rpc.logging import configure_logging

        configure_logging(self.log_formatter, self.log_handler, self.log_levels)
