import asyncio
import json
from collections.abc import Callable

import httpx
from fastapi import APIRouter, Request, Response
from slowapi import Limiter

from omni_rpc.domain.model.chain import Chain
from omni_rpc.domain.ports.cache import CachePort
from omni_rpc.domain.ports.chain_registry import ChainRegistryPort
from omni_rpc.domain.ports.logger import Logger
from omni_rpc.domain.ports.provider import (
    ProviderError,
    ProviderPort,
    ProviderTimeoutError,
)

JSON_CONTENT_TYPE = "application/json"

ProviderFactory = Callable[[Chain, httpx.AsyncClient], ProviderPort]


def _rpc_error(code: int, message: str, status: int) -> Response:
    body = json.dumps(
        {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": None}
    )
    return Response(content=body, status_code=status, media_type=JSON_CONTENT_TYPE)


def _parse_and_normalize(body: bytes) -> tuple[dict, str] | None:
    """Parse a JSON-RPC body; return a normalized payload dict and the method name."""
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    method = payload.get("method")
    if not isinstance(method, str):
        return None
    normalized = {
        "jsonrpc": "2.0",
        "id": payload.get("id"),
        "method": method,
        "params": payload.get("params", []),
    }
    return normalized, method


def _is_method_allowed(method: str, allowed_prefixes: set[str]) -> bool:
    namespace, _, _ = method.partition("_")
    if not namespace or namespace == method:
        return False
    return namespace in allowed_prefixes


def _build_cache_key(chain_key: str, method: str, normalized: dict) -> str:
    if method == "web3_sha3":
        return f"web3_sha3:{json.dumps(normalized.get('params', []), sort_keys=True)}"
    return f"{chain_key}:{method}"


async def _try_cache_get(
    cache: CachePort,
    cache_ttls: dict[str, int],
    chain_key: str,
    method: str,
    normalized: dict,
    logger: Logger,
) -> tuple[str | None, str | None]:
    """Return (cache_key, cached_value). cache_key is None for non-cacheable methods."""
    if method not in cache_ttls:
        return None, None
    key = _build_cache_key(chain_key, method, normalized)
    try:
        value = await cache.get(key)
        if value is not None:
            logger.debug("Cache HIT chain=%s method=%s", chain_key, method)
        else:
            logger.debug("Cache MISS chain=%s method=%s", chain_key, method)
        return key, value
    except Exception:
        logger.warning("Cache read failed for key=%s", key, exc_info=True)
        return key, None


async def _try_cache_set(
    cache: CachePort, key: str | None, value: str, ttl: int | None, logger: Logger
) -> None:
    if key is None or ttl is None:
        return
    try:
        await cache.set(key, value, ttl_seconds=ttl)
        logger.debug("Cache SET key=%s ttl=%ss", key, ttl)
    except Exception:
        logger.warning("Cache write failed for key=%s", key, exc_info=True)


def _validate_request(
    registry: ChainRegistryPort,
    chain_key: str,
    body: bytes,
    max_payload_bytes: int,
    allowed_method_prefixes: set[str],
    logger: Logger,
) -> tuple[Chain, dict, str] | Response:
    """Validate chain, payload size, and JSON-RPC structure.

    Returns (chain, normalized, method) on success or an error Response on failure.
    """
    chain = registry.get_by_key(chain_key)
    if chain is None:
        logger.warning("Unknown chain chain_key=%s", chain_key)
        return _rpc_error(-32001, f"Unknown chain: {chain_key}", 404)
    if not chain.rpcs:
        logger.warning("No RPC endpoints chain_key=%s", chain_key)
        return _rpc_error(-32002, f"No RPC endpoints for chain: {chain_key}", 502)
    if len(body) > max_payload_bytes:
        logger.warning(
            "Payload too large chain_key=%s size=%d limit=%d",
            chain_key,
            len(body),
            max_payload_bytes,
        )
        return _rpc_error(-32600, "Payload too large", 413)
    parsed = _parse_and_normalize(body)
    if parsed is None:
        logger.warning("Invalid JSON-RPC request chain_key=%s", chain_key)
        return _rpc_error(-32600, "Invalid Request", 400)
    normalized, method = parsed
    if not _is_method_allowed(method, allowed_method_prefixes):
        logger.warning("Blocked method chain_key=%s method=%s", chain_key, method)
        return _rpc_error(-32601, f"Method not allowed: {method}", 403)
    return chain, normalized, method


def router(
    registry: ChainRegistryPort,
    limiter: Limiter,
    rate_limit: str,
    allowed_method_prefixes: set[str],
    cache: CachePort,
    cache_ttls: dict[str, int],
    logger: Logger,
    provider_factory: ProviderFactory,
    max_payload_bytes: int = 65536,
    request_timeout_seconds: float = 30.0,
) -> APIRouter:
    r = APIRouter()

    @r.get("/chains")
    def list_chains():
        return [
            {
                "key": c.key,
                "name": c.name,
                "chain_id": c.chain_id,
                "vm_type": c.vm_type,
                "rpc_count": len(c.rpcs),
            }
            for c in registry.list()
        ]

    @r.post("/{chain_key}")
    @limiter.limit(rate_limit)
    async def proxy_rpc(chain_key: str, request: Request):
        body = await request.body()
        result = _validate_request(
            registry,
            chain_key,
            body,
            max_payload_bytes,
            allowed_method_prefixes,
            logger,
        )
        if isinstance(result, Response):
            return result
        chain, normalized, method = result

        normalized_body = json.dumps(normalized).encode()
        logger.debug("Proxying chain=%s method=%s", chain_key, method)

        cache_key, cached = await _try_cache_get(
            cache, cache_ttls, chain_key, method, normalized, logger
        )
        if cached is not None:
            return Response(
                content=cached, status_code=200, media_type=JSON_CONTENT_TYPE
            )

        http_client: httpx.AsyncClient = request.app.state.http_client
        provider = provider_factory(chain, http_client)

        try:
            prov_resp = await asyncio.wait_for(
                provider.send(normalized_body),
                timeout=request_timeout_seconds,
            )
        except TimeoutError:
            logger.error("Request timeout chain=%s method=%s", chain_key, method)
            return _rpc_error(-32003, "Request timeout", 504)
        except ProviderTimeoutError:
            logger.error(
                "All providers timed out chain=%s method=%s", chain_key, method
            )
            return _rpc_error(-32003, "Upstream RPC timeout", 504)
        except ProviderError:
            logger.error("All providers failed chain=%s method=%s", chain_key, method)
            return _rpc_error(-32004, "Upstream RPC error", 502)

        if prov_resp.status_code >= 400:
            logger.error(
                "All providers returned errors chain=%s method=%s last_status=%d",
                chain_key,
                method,
                prov_resp.status_code,
            )
            return Response(
                content=prov_resp.content,
                status_code=prov_resp.status_code,
                media_type=JSON_CONTENT_TYPE,
            )

        await _try_cache_set(
            cache, cache_key, prov_resp.content.decode(), cache_ttls.get(method), logger
        )
        return Response(
            content=prov_resp.content,
            status_code=prov_resp.status_code,
            media_type=JSON_CONTENT_TYPE,
        )

    return r
