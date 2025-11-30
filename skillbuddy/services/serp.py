"""SerpAPI job search client with simple quota tracking."""
from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple

import aiohttp
from cachetools import TTLCache

from skillbuddy.config import SERPAPI_MONTHLY_QUOTA, serpapi_key

SERP_ENDPOINT = "https://serpapi.com/search"
CACHE_TTL_SECONDS = 3600  # Cache for one hour to reduce quota usage


class SerpApiQuotaExceeded(RuntimeError):
    """Raised when the monthly request quota is exhausted."""


class SerpApiClient:
    def __init__(self) -> None:
        self._api_key = serpapi_key()
        self._cache: TTLCache[Tuple[str, str, int], Dict[str, Any]] = TTLCache(maxsize=128, ttl=CACHE_TTL_SECONDS)
        self._request_count = 0
        self._lock = asyncio.Lock()

    async def search_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        num_results: int = 10,
        fresh: bool = False,
    ) -> Dict[str, Any]:
        """Fetch job listings using SerpAPI's Google Jobs endpoint."""
        key = (query, location or "", num_results)
        if not fresh and key in self._cache:
            return self._cache[key]

        async with self._lock:
            if self._request_count >= SERPAPI_MONTHLY_QUOTA:
                raise SerpApiQuotaExceeded("SerpAPI monthly quota exhausted")
            self._request_count += 1

        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": self._api_key,
            "output": "json",
        }
        if location:
            params["location"] = location

        async with aiohttp.ClientSession() as session:
            async with session.get(SERP_ENDPOINT, params=params, timeout=30) as response:
                response.raise_for_status()
                payload: Dict[str, Any] = await response.json()

        # Trim results if necessary
        jobs = payload.get("jobs_results", [])[:num_results]
        payload["jobs_results"] = jobs
        self._cache[key] = payload
        return payload

    @property
    def remaining_quota(self) -> int:
        return max(SERPAPI_MONTHLY_QUOTA - self._request_count, 0)
