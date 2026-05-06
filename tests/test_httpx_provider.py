from unittest.mock import AsyncMock

import httpx
import pytest

from omni_rpc.adapters.outbound.httpx_provider import FailoverProvider, HttpxProvider
from omni_rpc.domain.model.chain import RpcEndpoint
from omni_rpc.domain.ports.provider import (
    ProviderError,
    ProviderNetworkError,
    ProviderPort,
    ProviderResponse,
    ProviderTimeoutError,
)

from .conftest import NullLogger

_ENDPOINT = RpcEndpoint(url="https://rpc.example.com", source="upstream")
_REQUEST = b'{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
_OK_RESPONSE = httpx.Response(200, json={"jsonrpc": "2.0", "result": "0x1", "id": 1})


def _mock_client(side_effect) -> AsyncMock:
    client = AsyncMock()
    client.post = AsyncMock(side_effect=side_effect)
    return client


def _make_provider(client, timeout=5.0, max_retries=0):
    return HttpxProvider(_ENDPOINT, client, timeout, max_retries, NullLogger())


class TestHttpxProvider:
    @pytest.mark.asyncio
    async def test_success_returns_response(self):
        client = _mock_client([_OK_RESPONSE])
        provider = _make_provider(client)

        result = await provider.send(_REQUEST)

        assert result.status_code == 200
        assert b"0x1" in result.content

    @pytest.mark.asyncio
    async def test_timeout_raises_provider_timeout_error(self):
        client = _mock_client([httpx.TimeoutException("timeout")])
        provider = _make_provider(client)

        with pytest.raises(ProviderTimeoutError):
            await provider.send(_REQUEST)

    @pytest.mark.asyncio
    async def test_network_error_raises_provider_network_error(self):
        client = _mock_client([httpx.ConnectError("refused")])
        provider = _make_provider(client)

        with pytest.raises(ProviderNetworkError):
            await provider.send(_REQUEST)

    @pytest.mark.asyncio
    async def test_4xx_response_is_returned_not_raised(self):
        bad_resp = httpx.Response(500, json={"error": "internal"})
        client = _mock_client([bad_resp])
        provider = _make_provider(client)

        result = await provider.send(_REQUEST)

        assert result.status_code == 500

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self):
        client = _mock_client([httpx.TimeoutException("t1"), _OK_RESPONSE])
        provider = _make_provider(client, max_retries=1)

        result = await provider.send(_REQUEST)

        assert result.status_code == 200
        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_exhausted_retries_raises(self):
        client = _mock_client(
            [httpx.TimeoutException("t1"), httpx.TimeoutException("t2")]
        )
        provider = _make_provider(client, max_retries=1)

        with pytest.raises(ProviderTimeoutError):
            await provider.send(_REQUEST)

        assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_health_returns_true_on_success(self):
        client = _mock_client([httpx.Response(200, json={"result": "0x1"})])
        provider = _make_provider(client)

        assert await provider.health() is True

    @pytest.mark.asyncio
    async def test_health_returns_false_on_error(self):
        client = _mock_client([httpx.TimeoutException("timeout")])
        provider = _make_provider(client)

        assert await provider.health() is False

    @pytest.mark.asyncio
    async def test_sends_correct_content_type(self):
        client = _mock_client([_OK_RESPONSE])
        provider = _make_provider(client)

        await provider.send(_REQUEST)

        _, kwargs = client.post.call_args
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["content"] == _REQUEST


class TestFailoverProvider:
    @pytest.mark.asyncio
    async def test_returns_first_success(self):
        p1 = _make_stub(ProviderResponse(b"ok", 200))
        p2 = _make_stub(ProviderResponse(b"ok2", 200))
        failover = FailoverProvider([p1, p2], NullLogger())

        result = await failover.send(_REQUEST)

        assert result.content == b"ok"

    @pytest.mark.asyncio
    async def test_skips_to_next_on_timeout(self):
        p1 = _make_stub(ProviderTimeoutError("timeout"))
        p2 = _make_stub(ProviderResponse(b"ok", 200))
        failover = FailoverProvider([p1, p2], NullLogger())

        result = await failover.send(_REQUEST)

        assert result.content == b"ok"

    @pytest.mark.asyncio
    async def test_skips_to_next_on_network_error(self):
        p1 = _make_stub(ProviderNetworkError("refused"))
        p2 = _make_stub(ProviderResponse(b"ok", 200))
        failover = FailoverProvider([p1, p2], NullLogger())

        result = await failover.send(_REQUEST)

        assert result.content == b"ok"

    @pytest.mark.asyncio
    async def test_skips_to_next_on_4xx(self):
        p1 = _make_stub(ProviderResponse(b"err", 500))
        p2 = _make_stub(ProviderResponse(b"ok", 200))
        failover = FailoverProvider([p1, p2], NullLogger())

        result = await failover.send(_REQUEST)

        assert result.content == b"ok"

    @pytest.mark.asyncio
    async def test_returns_last_error_response_when_all_fail_with_4xx(self):
        p1 = _make_stub(ProviderResponse(b"err1", 500))
        p2 = _make_stub(ProviderResponse(b"err2", 502))
        failover = FailoverProvider([p1, p2], NullLogger())

        result = await failover.send(_REQUEST)

        assert result.status_code == 502
        assert result.content == b"err2"

    @pytest.mark.asyncio
    async def test_raises_last_exc_when_all_providers_raise(self):
        p1 = _make_stub(ProviderTimeoutError("t1"))
        p2 = _make_stub(ProviderNetworkError("n2"))
        failover = FailoverProvider([p1, p2], NullLogger())

        with pytest.raises(ProviderNetworkError):
            await failover.send(_REQUEST)

    @pytest.mark.asyncio
    async def test_raises_when_no_providers(self):
        failover = FailoverProvider([], NullLogger())

        with pytest.raises(ProviderError):
            await failover.send(_REQUEST)

    @pytest.mark.asyncio
    async def test_health_true_if_any_healthy(self):
        p1 = _make_stub_health(False)
        p2 = _make_stub_health(True)
        failover = FailoverProvider([p1, p2], NullLogger())

        assert await failover.health() is True

    @pytest.mark.asyncio
    async def test_health_false_if_all_unhealthy(self):
        p1 = _make_stub_health(False)
        p2 = _make_stub_health(False)
        failover = FailoverProvider([p1, p2], NullLogger())

        assert await failover.health() is False


class _StubProvider(ProviderPort):
    def __init__(self, outcome, healthy: bool = True):
        self._outcome = outcome
        self._healthy = healthy

    async def send(self, request: bytes) -> ProviderResponse:
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    async def health(self) -> bool:
        return self._healthy


def _make_stub(outcome) -> ProviderPort:
    return _StubProvider(outcome)


def _make_stub_health(healthy: bool) -> ProviderPort:
    return _StubProvider(ProviderResponse(b"", 200), healthy=healthy)
