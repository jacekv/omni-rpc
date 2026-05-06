import redis.asyncio as redis

from omni_rpc.domain.ports.cache import CachePort
from omni_rpc.domain.ports.logger import Logger
from omni_rpc.logging import LoggerFactory


class RedisCacheAdapter(CachePort):
    def __init__(self, url: str, logger_factory: LoggerFactory):
        self._client = redis.from_url(url)
        self._logger: Logger = logger_factory.get_logger(
            "omni_rpc.adapters.outbound.redis_cache"
        )
        self._logger.info("Redis cache adapter initialized with url=%s", url)

    async def get(self, key: str) -> str | None:
        value = await self._client.get(key)
        if value is None:
            self._logger.debug("Cache MISS for key=%s", key)
            return None
        self._logger.debug("Cache HIT for key=%s", key)
        return value.decode() if isinstance(value, bytes) else value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        if ttl_seconds is not None:
            await self._client.setex(key, ttl_seconds, value)
        else:
            await self._client.set(key, value)
        self._logger.debug("Cache SET key=%s ttl=%s", key, ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)
        self._logger.debug("Cache DELETE key=%s", key)

    async def close(self) -> None:
        await self._client.aclose()
        self._logger.info("Redis cache adapter closed")
