import json
from collections.abc import Sequence

import httpx

from omni_rpc.domain.model.chain import RpcEndpoint
from omni_rpc.domain.ports.logger import Logger
from omni_rpc.domain.ports.provider import (
    ProviderError,
    ProviderNetworkError,
    ProviderPort,
    ProviderResponse,
    ProviderTimeoutError,
)

_HEALTH_PAYLOAD = json.dumps(
    {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}
).encode()
_JSON_CONTENT_TYPE = "application/json"


class HttpxProvider(ProviderPort):
    def __init__(
        self,
        endpoint: RpcEndpoint,
        client: httpx.AsyncClient,
        timeout: float,
        max_retries: int,
        logger: Logger,
    ) -> None:
        self._endpoint = endpoint
        self._client = client
        self._timeout = timeout
        self._max_retries = max_retries
        self._logger = logger

    async def send(self, request: bytes) -> ProviderResponse:
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                resp = await self._client.post(
                    self._endpoint.url,
                    content=request,
                    headers={"Content-Type": _JSON_CONTENT_TYPE},
                    timeout=self._timeout,
                )
                self._logger.debug(
                    "Provider response url=%s status=%s attempt=%d",
                    self._endpoint.url,
                    resp.status_code,
                    attempt,
                )
                return ProviderResponse(
                    content=resp.content, status_code=resp.status_code
                )
            except httpx.TimeoutException as exc:
                self._logger.warning(
                    "Provider timeout url=%s attempt=%d", self._endpoint.url, attempt
                )
                last_exc = exc
            except httpx.HTTPError as exc:
                self._logger.warning(
                    "Provider network error url=%s error=%s attempt=%d",
                    self._endpoint.url,
                    exc,
                    attempt,
                )
                last_exc = exc

        attempts = self._max_retries + 1
        if isinstance(last_exc, httpx.TimeoutException):
            raise ProviderTimeoutError(
                f"Provider timed out after {attempts} attempt(s): {self._endpoint.url}"
            ) from last_exc
        raise ProviderNetworkError(
            f"Provider network error after {attempts} attempt(s): {self._endpoint.url}"
        ) from last_exc

    async def health(self) -> bool:
        try:
            resp = await self._client.post(
                self._endpoint.url,
                content=_HEALTH_PAYLOAD,
                headers={"Content-Type": _JSON_CONTENT_TYPE},
                timeout=self._timeout,
            )
            return resp.status_code < 400
        except Exception:
            return False


class FailoverProvider(ProviderPort):
    def __init__(self, providers: Sequence[ProviderPort], logger: Logger) -> None:
        self._providers = providers
        self._logger = logger

    async def send(self, request: bytes) -> ProviderResponse:
        last_response: ProviderResponse | None = None
        last_exc: ProviderError | None = None

        for provider in self._providers:
            try:
                resp = await provider.send(request)
            except ProviderError as exc:
                self._logger.warning("Provider failed, trying next: %s", exc)
                last_exc = exc
                continue

            if resp.status_code >= 400:
                self._logger.warning(
                    "Provider returned error status=%d, trying next", resp.status_code
                )
                last_response = resp
                continue

            return resp

        if last_response is not None:
            return last_response
        if last_exc is not None:
            raise last_exc
        raise ProviderError("No providers configured")

    async def health(self) -> bool:
        for provider in self._providers:
            if await provider.health():
                return True
        return False
