from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from .config import settings


def _guess_mime(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".png"):
        return "image/png"
    if name.endswith(".webp"):
        return "image/webp"
    if name.endswith(".jpg") or name.endswith(".jpeg"):
        return "image/jpeg"
    if name.endswith(".gif"):
        return "image/gif"
    return "application/octet-stream"


@dataclass(frozen=True)
class KieClient:
    api_key: str
    api_base: str = "https://api.kie.ai"
    file_upload_base: str = "https://kieai.redpandaai.co"

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            raise RuntimeError("KIE_API_KEY is not set")
        return {"Authorization": f"Bearer {self.api_key}"}

    async def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/jobs/createTask"
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(url, json=payload, headers={**self._headers(), "Content-Type": "application/json"})
            res.raise_for_status()
            return res.json()

    async def record_info(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/jobs/recordInfo"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(url, params={"taskId": task_id}, headers=self._headers())
            res.raise_for_status()
            return res.json()

    async def gpt4o_image_generate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/gpt4o-image/generate"
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(url, json=payload, headers={**self._headers(), "Content-Type": "application/json"})
            res.raise_for_status()
            return res.json()

    async def gpt4o_image_record_info(self, task_id: str) -> Dict[str, Any]:
        url = f"{self.api_base.rstrip('/')}/api/v1/gpt4o-image/record-info"
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(url, params={"taskId": task_id}, headers=self._headers())
            res.raise_for_status()
            return res.json()

    async def file_url_upload(self, file_url: str, *, upload_path: str = "primerch") -> Dict[str, Any]:
        url = f"{self.file_upload_base.rstrip('/')}/api/file-url-upload"
        # KIE expects `fileUrl` (downloadable URL).
        # Some deployments also accept `url`, so we send both for compatibility.
        payload = {"fileUrl": file_url, "url": file_url, "uploadPath": upload_path}
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(url, json=payload, headers={**self._headers(), "Content-Type": "application/json"})
            res.raise_for_status()
            return res.json()

    async def file_stream_upload(self, file_path: Path, *, upload_path: str = "primerch") -> Dict[str, Any]:
        url = f"{self.file_upload_base.rstrip('/')}/api/file-stream-upload"
        mime = _guess_mime(file_path.name)
        files = {"file": (file_path.name, file_path.read_bytes(), mime)}
        data = {"uploadPath": upload_path}
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(url, data=data, files=files, headers=self._headers())
            res.raise_for_status()
            return res.json()


def get_client() -> KieClient:
    return KieClient(
        api_key=settings.KIE_API_KEY,
        api_base=settings.KIE_API_BASE,
        file_upload_base=settings.KIE_FILE_UPLOAD_BASE,
    )


def parse_result_json(result_json: Any) -> Optional[Dict[str, Any]]:
    if not result_json:
        return None
    if isinstance(result_json, dict):
        return result_json
    if isinstance(result_json, str):
        try:
            return json.loads(result_json)
        except Exception:
            return None
    return None


def extract_uploaded_file_url(resp: Dict[str, Any]) -> Optional[str]:
    data = resp.get("data") or {}
    if not isinstance(data, dict):
        return None
    for key in ("fileUrl", "url", "downloadUrl", "download_url"):
        val = data.get(key)
        if val:
            return str(val)
    return None