from omni_rpc.domain.ports.cache import CachePort


class NullCacheAdapter(CachePort):
    """No-op cache used when no Redis URL is configured."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def close(self) -> None:
        pass
