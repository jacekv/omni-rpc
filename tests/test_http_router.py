import json as _json

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from omni_rpc.adapters.inbound.http import ProviderFactory, router
from omni_rpc.adapters.outbound.in_memory_chain_registry import InMemoryChainRegistry
from omni_rpc.adapters.outbound.null_cache import NullCacheAdapter
from omni_rpc.domain.model.chain import Chain, RpcEndpoint
from omni_rpc.domain.ports.provider import (
    ProviderNetworkError,
    ProviderPort,
    ProviderResponse,
    ProviderTimeoutError,
)

from .conftest import NullLogger, make_chain

DEFAULT_ALLOWED_PREFIXES = {"eth", "net", "web3"}

_SUCCESS_RESPONSE = ProviderResponse(
    content=_json.dumps({"jsonrpc": "2.0", "result": "0x10", "id": 1}).encode(),
    status_code=200,
)


class StubProvider(ProviderPort):
    def __init__(
        self,
        responses: list[ProviderResponse | Exception] | None = None,
    ) -> None:
        self._responses = list(responses or [_SUCCESS_RESPONSE])
        self._index = 0
        self.received: list[bytes] = []

    async def send(self, request: bytes) -> ProviderResponse:
        self.received.append(request)
        resp = self._responses[self._index % len(self._responses)]
        self._index += 1
        if isinstance(resp, Exception):
            raise resp
        return resp

    async def health(self) -> bool:
        return True


def _stub_factory(
    provider: StubProvider,
) -> ProviderFactory:
    def factory(chain: Chain, client: httpx.AsyncClient) -> ProviderPort:
        return provider

    return factory


def _create_test_app(
    registry: InMemoryChainRegistry,
    provider_factory: ProviderFactory | None = None,
    allowed_method_prefixes: set[str] | None = None,
    max_payload_bytes: int = 65536,
    request_timeout_seconds: float = 30.0,
) -> FastAPI:
    limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
    prefixes = allowed_method_prefixes or DEFAULT_ALLOWED_PREFIXES

    if provider_factory is None:
        provider_factory = _stub_factory(StubProvider())

    app = FastAPI()
    app.state.limiter = limiter
    app.state.http_client = httpx.AsyncClient()
    app.include_router(
        router(
            registry,
            limiter,
            "100/minute",
            prefixes,
            NullCacheAdapter(),
            {},
            NullLogger(),
            provider_factory=provider_factory,
            max_payload_bytes=max_payload_bytes,
            request_timeout_seconds=request_timeout_seconds,
        )
    )
    return app


class TestListChains:
    def test_empty_registry(self):
        registry = InMemoryChainRegistry()
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.get("/chains")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_registered_chains(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum", chain_id=1, name="Ethereum"))
        registry.register(
            make_chain(
                key="polygon",
                chain_id=137,
                name="Polygon",
                rpcs=[
                    RpcEndpoint(url="https://rpc1.example.com", source="upstream"),
                    RpcEndpoint(url="https://rpc2.example.com", source="upstream"),
                ],
            )
        )
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.get("/chains")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        eth = next(c for c in data if c["key"] == "ethereum")
        assert eth["name"] == "Ethereum"
        assert eth["chain_id"] == 1
        assert eth["rpc_count"] == 1

        poly = next(c for c in data if c["key"] == "polygon")
        assert poly["rpc_count"] == 2


class TestProxyRpc:
    def test_unknown_chain_returns_error(self):
        registry = InMemoryChainRegistry()
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/nonexistent",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 404
        body = response.json()
        assert body["error"]["code"] == -32001
        assert "Unknown chain" in body["error"]["message"]

    def test_chain_with_no_rpcs_returns_502(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="empty-chain", rpcs=[]))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/empty-chain",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 502
        body = response.json()
        assert body["error"]["code"] == -32002

    def test_successful_proxy(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result"] == "0x10"

    def test_all_rpcs_fail_returns_timeout_error(self):
        stub = StubProvider(responses=[ProviderTimeoutError("timeout")])
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry, provider_factory=_stub_factory(stub))
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 504
        body = response.json()
        assert body["error"]["code"] == -32003

    def test_network_error_returns_502(self):
        stub = StubProvider(responses=[ProviderNetworkError("conn refused")])
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry, provider_factory=_stub_factory(stub))
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 502
        body = response.json()
        assert body["error"]["code"] == -32004

    def test_upstream_error_response_is_passed_through(self):
        stub = StubProvider(
            responses=[
                ProviderResponse(
                    content=_json.dumps({"error": "internal"}).encode(),
                    status_code=500,
                ),
            ]
        )
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry, provider_factory=_stub_factory(stub))
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 500

    def test_blocked_method_returns_error(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry, allowed_method_prefixes={"eth"})
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "debug_traceTransaction", "id": 1},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == -32601
        assert "debug_traceTransaction" in body["error"]["message"]

    def test_method_without_namespace_rejected(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "blockNumber", "id": 1},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["error"]["code"] == -32601

    def test_invalid_json_body_returns_error(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == -32600

    def test_missing_method_field_returns_error(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "id": 1},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["error"]["code"] == -32600


class TestPayloadSize:
    def test_oversized_payload_returns_error(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry, max_payload_bytes=10)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            content=b"x" * 11,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 413
        body = response.json()
        assert body["error"]["code"] == -32600
        assert "too large" in body["error"]["message"]

    def test_payload_within_limit_passes_guard(self):
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        app = _create_test_app(registry)
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 200


class TestNormalization:
    def _make_app_with_capture(self) -> tuple[FastAPI, StubProvider]:
        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))
        stub = StubProvider()
        app = _create_test_app(registry, provider_factory=_stub_factory(stub))
        return app, stub

    def test_missing_jsonrpc_field_is_filled(self):
        app, stub = self._make_app_with_capture()
        client = TestClient(app)

        client.post("/ethereum", json={"method": "eth_blockNumber", "id": 1})

        payload = _json.loads(stub.received[0])
        assert payload["jsonrpc"] == "2.0"

    def test_missing_params_defaults_to_empty_list(self):
        app, stub = self._make_app_with_capture()
        client = TestClient(app)

        client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )

        payload = _json.loads(stub.received[0])
        assert payload["params"] == []

    def test_missing_id_defaults_to_null(self):
        app, stub = self._make_app_with_capture()
        client = TestClient(app)

        client.post("/ethereum", json={"jsonrpc": "2.0", "method": "eth_blockNumber"})

        payload = _json.loads(stub.received[0])
        assert payload["id"] is None

    def test_extra_fields_are_stripped(self):
        app, stub = self._make_app_with_capture()
        client = TestClient(app)

        client.post(
            "/ethereum",
            json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "id": 1,
                "extra": "noise",
            },
        )

        payload = _json.loads(stub.received[0])
        assert "extra" not in payload
        assert set(payload.keys()) == {"jsonrpc", "id", "method", "params"}


class TestRequestTimeout:
    def test_overall_timeout_returns_error(self):
        import asyncio

        async def _slow(request: bytes) -> ProviderResponse:
            await asyncio.sleep(10)
            return _SUCCESS_RESPONSE  # pragma: no cover

        class SlowProvider(ProviderPort):
            async def send(self, request: bytes) -> ProviderResponse:
                return await _slow(request)

            async def health(self) -> bool:
                return True

        registry = InMemoryChainRegistry()
        registry.register(make_chain(key="ethereum"))

        def slow_factory(chain: Chain, client: httpx.AsyncClient) -> ProviderPort:
            return SlowProvider()

        app = _create_test_app(
            registry,
            provider_factory=slow_factory,
            request_timeout_seconds=0.01,
        )
        client = TestClient(app)

        response = client.post(
            "/ethereum",
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "id": 1},
        )
        assert response.status_code == 504
        body = response.json()
        assert body["error"]["code"] == -32003
        assert "timeout" in body["error"]["message"].lower()
