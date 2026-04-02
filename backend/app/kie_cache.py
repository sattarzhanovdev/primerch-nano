from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CacheEntry:
    url: str
    created_at: float


class KieUploadCache:
    """
    Tiny disk-backed cache for mapping a source URL (or local uploads URL) to a KIE tempfile URL.
    KIE temp URLs expire; we keep a conservative TTL.
    """

    def __init__(self, path: Path, *, ttl_seconds: int = int(60 * 60 * 24 * 2.5)) -> None:
        self._path = path
        self._ttl = ttl_seconds

    def _load(self) -> dict[str, CacheEntry]:
        if not self._path.exists():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            out: dict[str, CacheEntry] = {}
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if not isinstance(v, dict):
                        continue
                    url = v.get("url")
                    created_at = v.get("created_at")
                    if isinstance(url, str) and isinstance(created_at, (int, float)):
                        out[str(k)] = CacheEntry(url=url, created_at=float(created_at))
            return out
        except Exception:
            return {}

    def _save(self, data: dict[str, CacheEntry]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        raw = {k: {"url": v.url, "created_at": v.created_at} for k, v in data.items()}
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._path)

    def get(self, key: str) -> Optional[str]:
        now = time.time()
        data = self._load()
        entry = data.get(key)
        if not entry:
            return None
        if now - entry.created_at > self._ttl:
            # expired
            data.pop(key, None)
            self._save(data)
            return None
        return entry.url

    def set(self, key: str, value: str) -> None:
        now = time.time()
        data = self._load()
        data[key] = CacheEntry(url=value, created_at=now)
        # trim (keep last ~300)
        if len(data) > 300:
            items = sorted(data.items(), key=lambda kv: kv[1].created_at, reverse=True)[:300]
            data = dict(items)
        self._save(data)

