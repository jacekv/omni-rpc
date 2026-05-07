# omni-rpc

A JSON-RPC proxy service that aggregates blockchain RPC endpoints from [ethereum-lists/chains](https://github.com/ethereum-lists/chains) and exposes them through a unified FastAPI interface.

**Single endpoint, any chain.** Instead of managing a separate RPC URL per network, clients POST to `/{chain_key}` and omni-rpc handles endpoint selection, failover, caching, and rate limiting transparently.

## What it covers

### Routing & proxying
- Unified `POST /{chain_key}` endpoint for any chain loaded from ethereum-lists
- `GET /chains` lists all registered chains with metadata
- JSON-RPC request normalisation (fills missing `jsonrpc`, `id`, `params` fields; strips unknown fields)
- Blocked namespaces: `trace_*` and `debug_*` methods are rejected before they reach any provider

### Provider abstraction
- `ProviderPort` interface (`send` / `health`) decouples the HTTP layer from outbound transport
- `HttpxProvider` sends requests to a single RPC endpoint with a configurable hard timeout and per-provider retries
- `FailoverProvider` wraps multiple providers per chain and tries each in order, masking individual failures from the caller

### Reliability
- Failover across all RPC endpoints for a chain on timeout, network error, or upstream 4xx/5xx
- Per-request overall timeout independent of per-provider timeout
- Rate limiting via slowapi (configurable per environment)

### Caching
- Redis-backed cache for deterministic methods (`eth_chainId`, `net_version`, `web3_clientVersion`, `web3_sha3`, `net_listening`)
- Per-chain cache namespacing and per-method TTLs
- Graceful degradation to no-op cache when Redis is unavailable

### Chain registry
- Loads chain definitions from the ethereum-lists git repo at startup
- Validates schema, detects duplicate chain IDs and names, logs checksum
- Read-only registry for consumers; atomic swap on reload with rollback on failure
- Background sync loop keeps chain data fresh without restarts

### Request validation
- Rejects unknown chains (404) and chains with no configured endpoints (502)
- Enforces configurable max payload size
- Validates JSON-RPC structure before forwarding

### Architecture
Hexagonal (ports & adapters): domain model and port interfaces are framework-free; adapters are injected at startup. This makes all layers independently testable.

```
domain/
  model/      — Chain, RpcEndpoint, VmType (immutable dataclasses)
  ports/      — ChainLoaderPort, ChainRegistryPort, CachePort, ProviderPort, Logger

application/  — LoadChainsUseCase, SyncChainsUseCase, BootstrapEthereumLists

adapters/
  inbound/    — FastAPI router
  outbound/   — EthereumListsChainLoader, InMemoryChainRegistry,
                HttpxProvider, FailoverProvider,
                RedisCacheAdapter, NullCacheAdapter
```

---

## Setup

```
poetry install
poetry run omni-rpc init-chains
```

This will install the dependencies and download the ethereum-lists/chains repository.

## Start the service

```
poetry run python -m omni_rpc.main
```

By default this starts the server on `127.0.0.1:8000` using the `dev` environment config.

To use a different environment:

```
poetry run python -m omni_rpc.main --environment staging
poetry run python -m omni_rpc.main --environment prod
```

## Tests

```
poetry run pytest
```

## Configuration

Environment-specific config files live in `config/`:

```
config/
├── config.template.yaml   # Documented template
├── dev.yaml
├── staging.yaml
└── prod.yaml
```

See `config/config.template.yaml` for available settings and their descriptions.
