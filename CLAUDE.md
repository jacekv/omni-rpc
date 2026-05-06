# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Omni-RPC

A JSON-RPC proxy service that aggregates blockchain RPC endpoints from ethereum-lists and exposes them through a unified FastAPI interface with failover and rate limiting.

## Development Commands

```bash
# Install dependencies
poetry install

# Bootstrap chain data (clones ethereum-lists repo to data/)
poetry run omni-rpc init-chains

# Run dev server (127.0.0.1:8000, auto-reload, DEBUG logging)
poetry run python -m omni_rpc.main

# Run with specific environment config
poetry run python -m omni_rpc.main --environment staging
poetry run python -m omni_rpc.main --environment prod

# Generate/validate OpenAPI spec
poetry run python -m scripts.generate_openapi

# Pre-commit hooks (black, isort, flake8, mypy, bandit, pyupgrade)
pre-commit run --all-files
```

## Testing

Every change requires unit tests and all tests must pass. Tests live in `tests/` and use pytest.

```bash
# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/test_load_chains.py

# Run a specific test
poetry run pytest tests/test_load_chains.py::test_something -v
```

The hexagonal architecture makes testing straightforward: inject fake/mock adapters through ports to test use cases and domain logic without external dependencies.

## Architecture

Hexagonal architecture (ports & adapters) with three layers:

- **Domain** (`domain/model/`, `domain/ports/`) — immutable dataclasses (`Chain`, `RpcEndpoint`, `VmType` enum) and abstract port interfaces (`ChainLoaderPort`, `ChainRegistryPort`, `Logger`)
- **Application** (`application/`) — use cases that orchestrate domain logic: `LoadChainsUseCase` loads chains from a loader into a registry; `BootstrapEthereumLists` clones the ethereum-lists git repo
- **Adapters** — concrete implementations of ports:
  - **Inbound** (`adapters/inbound/http.py`) — FastAPI router: `GET /chains` lists chains, `POST /{chain_key}` proxies JSON-RPC with failover across endpoints and rate limiting via slowapi
  - **Outbound** — `EthereumListsChainLoader` reads chain JSON files, `InMemoryChainRegistry` stores chains in a dict, `PythonLogger` wraps stdlib logging

**Startup flow:** `main.py` parses `--environment` arg → loads `config/{env}.yaml` via `Settings` → runs uvicorn → `_app.py:create_app()` wires all adapters together → lifespan context manager loads chains on startup and creates a shared `httpx.AsyncClient`.

## Configuration

YAML files in `config/` (dev.yaml, staging.yaml, prod.yaml). Template at `config/config.template.yaml`. Key settings: `data_dir`, `rate_limit`, `api.host/port/workers/reload`, `logging.formatter/handler/levels`.

## Code Style

- Python 3.11+, max line length 88 (black + flake8)
- isort for import ordering, mypy for type checking, bandit for security
- All enforced via pre-commit hooks
