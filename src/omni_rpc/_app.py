import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from omni_rpc.adapters.inbound.http import ProviderFactory, router
from omni_rpc.adapters.outbound.ethereum_lists_loader import EthereumListsChainLoader
from omni_rpc.adapters.outbound.httpx_provider import FailoverProvider, HttpxProvider
from omni_rpc.adapters.outbound.in_memory_chain_registry import InMemoryChainRegistry
from omni_rpc.adapters.outbound.null_cache import NullCacheAdapter
from omni_rpc.adapters.outbound.redis_cache import RedisCacheAdapter
from omni_rpc.application.load_chains import LoadChainsUseCase
from omni_rpc.application.sync_chains import SyncChainsUseCase
from omni_rpc.application.update_chains import UpdateEthereumLists
from omni_rpc.config.settings import parse_and_load_environment_settings
from omni_rpc.domain.model.chain import Chain
from omni_rpc.domain.ports.cache import CachePort
from omni_rpc.domain.ports.logger import Logger
from omni_rpc.logging import LoggerFactory


def _make_provider_factory(
    upstream_timeout_seconds: float,
    logger: Logger,
) -> ProviderFactory:
    def factory(chain: Chain, client: httpx.AsyncClient) -> FailoverProvider:
        providers = [
            HttpxProvider(rpc, client, upstream_timeout_seconds, 0, logger)
            for rpc in chain.rpcs
        ]
        return FailoverProvider(providers, logger)

    return factory


def _rate_limit_handler(request, exc: RateLimitExceeded):
    retry_after = exc.detail.split(" ")[-1] if exc.detail else ""
    return JSONResponse(
        status_code=429,
        content={
            "jsonrpc": "2.0",
            "error": {
                "code": -32005,
                "message": "Rate limit exceeded",
            },
            "id": None,
        },
        headers={"Retry-After": retry_after},
    )


async def _sync_loop(sync_uc: SyncChainsUseCase, interval: int, logger: Logger) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            sync_uc.execute()
        except Exception:
            logger.error("Chain sync failed", exc_info=True)


def create_app() -> FastAPI:
    settings = parse_and_load_environment_settings()
    settings.configure_logging()

    logger_factory = LoggerFactory()
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    registry = InMemoryChainRegistry()

    loader = EthereumListsChainLoader(
        chains_dir=settings.chains_dir,
        logger=logger_factory.get_logger("EthereumListsChainLoader"),
    )

    cache: CachePort
    if settings.redis_url:
        cache = RedisCacheAdapter(settings.redis_url, logger_factory)
    else:
        cache = NullCacheAdapter()

    sync_uc = SyncChainsUseCase(
        updater=UpdateEthereumLists(
            target_dir=settings.data_dir / "ethereum-lists",
            logger=logger_factory.get_logger("UpdateEthereumLists"),
        ),
        loader=loader,
        registry=registry,
        logger=logger_factory.get_logger("SyncChainsUseCase"),
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        LoadChainsUseCase(
            loader=loader,
            registry=registry,
            chains_dir=settings.chains_dir,
            logger=logger_factory.get_logger("LoadChainsUseCase"),
        ).execute()
        sync_task = asyncio.create_task(
            _sync_loop(
                sync_uc,
                settings.chain_sync_interval,
                logger_factory.get_logger("ChainSyncLoop"),
            )
        )
        async with httpx.AsyncClient() as client:
            app.state.http_client = client
            try:
                yield
            finally:
                sync_task.cancel()
                await cache.close()

    app = FastAPI(
        title="OmniRPC",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    provider_logger = logger_factory.get_logger("omni_rpc.adapters.outbound.provider")
    app.include_router(
        router(
            registry,
            limiter,
            settings.rate_limit,
            settings.allowed_method_prefixes,
            cache,
            settings.cache_ttls,
            logger_factory.get_logger("omni_rpc.adapters.inbound.http"),
            provider_factory=_make_provider_factory(
                settings.upstream_timeout_seconds, provider_logger
            ),
            max_payload_bytes=settings.max_payload_bytes,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
    )
    return app


app = create_app()
