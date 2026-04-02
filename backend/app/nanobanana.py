from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from .config import settings


@dataclass(frozen=True)
class NanoBananaClient:
    api_key: str
    api_base: str = "https://api.nanobananaapi.ai"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("NANOBANANA_API_KEY is not set")
        return {"Authorization": f"Bearer {self.api_key}"}

    async def generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/nanobanana/generate"
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(url, json=payload, headers=self._headers())
            res.raise_for_status()
            return res.json()

    async def record_info(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/nanobanana/record-info"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                url,
                params={"taskId": task_id},
                headers=self._headers(),
            )
            res.raise_for_status()
            return res.json()


def get_client() -> NanoBananaClient:
    return NanoBananaClient(api_key=settings.NANOBANANA_API_KEY, api_base=settings.NANOBANANA_API_BASE)

