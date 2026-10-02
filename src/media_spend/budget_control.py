from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class BudgetControl:
    def __init__(self, api_key: str, base_url: str, max_attempts: int = 3) -> None:
        self._base_url = base_url.rstrip("/")
        self._max_attempts = max_attempts
        self._client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {api_key}"}, timeout=15.0
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def set_monthly_cap(
        self, hard_cap_usd: float, alert_threshold_usd: float
    ) -> dict[str, Any]:
        return await self._request(
            method="PUT",
            path="/account/budget/set",
            json={
                "hard_cap_usd": hard_cap_usd,
                "period": "monthly",
                "alert_threshold_usd": alert_threshold_usd,
            },
        )

    async def get_budget(self) -> dict[str, Any]:
        return await self._request(method="GET", path="/account/budget/get")

    async def _request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = await self._client.request(method=method, url=self._base_url + path, json=json)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self._max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise InfraiError(
                    code=str(error.get("code", "request_rejected")),
                    detail=error,
                    status_code=response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("retry loop exhausted")
