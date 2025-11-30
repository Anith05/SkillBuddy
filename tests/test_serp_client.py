import asyncio
from typing import Any, Dict, List

import pytest

from skillbuddy.services.serp import SerpApiClient, SerpApiQuotaExceeded


class DummyResponse:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self._payload = payload

    async def __aenter__(self) -> "DummyResponse":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def raise_for_status(self) -> None:
        return None

    async def json(self) -> Dict[str, Any]:
        return self._payload


class DummySession:
    def __init__(self, payload: Dict[str, Any], log: List[Dict[str, Any]]) -> None:
        self._payload = payload
        self._log = log

    async def __aenter__(self) -> "DummySession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def get(self, url: str, params: Dict[str, Any], timeout: int):
        self._log.append({"url": url, "params": params, "timeout": timeout})
        return DummyResponse(self._payload)


def test_search_jobs_uses_cache(monkeypatch):
    payload = {"jobs_results": [{"title": "Role"}, {"title": "Role 2"}, {"title": "Role 3"}]}
    log: List[Dict[str, Any]] = []

    def session_factory():
        return DummySession(payload, log)

    monkeypatch.setattr("skillbuddy.services.serp.aiohttp.ClientSession", session_factory)

    client = SerpApiClient()

    async def runner():
        result_first = await client.search_jobs("python developer", location="Remote", num_results=2)
        assert len(log) == 1
        assert len(result_first["jobs_results"]) == 2

        result_cached = await client.search_jobs("python developer", location="Remote", num_results=2)
        assert len(log) == 1  # cache hit, no extra HTTP call
        assert result_cached == result_first

        result_fresh = await client.search_jobs(
            "python developer", location="Remote", num_results=2, fresh=True
        )
        assert len(log) == 2
        assert result_fresh == result_first

    asyncio.run(runner())


def test_quota_exceeded(monkeypatch):
    def session_factory():
        pytest.fail("HTTP request should not happen when quota exceeded")

    monkeypatch.setattr("skillbuddy.services.serp.aiohttp.ClientSession", session_factory)

    client = SerpApiClient()
    async def run():
        client._request_count = client._request_count + client.remaining_quota
        with pytest.raises(SerpApiQuotaExceeded):
            await client.search_jobs("anything")

    asyncio.run(run())
