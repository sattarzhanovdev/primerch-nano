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


def extract_result_urls_any(resp: Any) -> list[str]:
    """
    Best-effort extraction of result image URLs across different KIE endpoints.
    """
    def _is_url(s: Any) -> bool:
        return isinstance(s, str) and s.startswith("http")

    def _scan(node: Any, *, depth: int) -> list[str]:
        if depth <= 0:
            return []
        out: list[str] = []
        if isinstance(node, dict):
            # High-signal keys first.
            for key in ("resultUrls", "result_urls", "resultUrl", "result_url"):
                val = node.get(key)
                if isinstance(val, list):
                    out.extend([str(u) for u in val if _is_url(u)])
                elif _is_url(val):
                    out.append(str(val))
            for key in ("images", "imageUrls", "image_urls", "urls"):
                val = node.get(key)
                if isinstance(val, list):
                    for it in val:
                        if _is_url(it):
                            out.append(str(it))
                        elif isinstance(it, dict):
                            u = it.get("url") or it.get("imageUrl") or it.get("image_url")
                            if _is_url(u):
                                out.append(str(u))
            # Recurse into common nested containers (gpt4o-image uses `data.response.resultUrls`,
            # callbacks may use `data.info.result_urls`).
            for k, v in node.items():
                if k in {"resultUrls", "result_urls", "images", "imageUrls", "image_urls"}:
                    continue
                if isinstance(v, (dict, list)):
                    out.extend(_scan(v, depth=depth - 1))
        elif isinstance(node, list):
            for it in node:
                if _is_url(it):
                    out.append(str(it))
                elif isinstance(it, (dict, list)):
                    out.extend(_scan(it, depth=depth - 1))
        return out

    if not isinstance(resp, dict):
        return []
    urls = _scan(resp, depth=5)
    # Deduplicate but preserve order.
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq


def extract_uploaded_file_url(resp: Dict[str, Any]) -> Optional[str]:
    data = resp.get("data") or {}
    if not isinstance(data, dict):
        return None
    for key in ("fileUrl", "url", "downloadUrl", "download_url"):
        val = data.get(key)
        if val:
            return str(val)
    return None
