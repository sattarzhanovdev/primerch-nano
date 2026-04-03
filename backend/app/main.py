from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import sys
from urllib.parse import urlparse

import httpx
from fastapi import BackgroundTasks, Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from .kie import extract_result_urls_any, extract_uploaded_file_url, get_client, parse_result_json
from .prompts import PromptInputs, build_nanobanana_prompt
from .config import settings
from .kie_cache import KieUploadCache
from .storage import build_file_url, repo_root, save_upload_image, uploads_dir
from .text_image import render_text_png
from .url_utils import is_public_http_url


app = FastAPI(title="Primerch KIE Image API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_callback_store: Dict[str, Any] = {}
_kie_cache = KieUploadCache(repo_root() / "uploads" / "kie_upload_cache.json")


@dataclass
class GenerateJob:
    job_id: str
    created_at: float
    updated_at: float
    state: str  # queued|submitting|submitted|failed
    provider: str = "kie_gpt4o_image"  # kie_jobs | kie_gpt4o_image
    error: str = ""
    kie_task_id: str = ""
    request_payload: Optional[Dict[str, Any]] = None


_jobs: Dict[str, GenerateJob] = {}


def _base_json_path() -> Path:
    return repo_root() / "base.json"

def _coerce_provider(payload: Dict[str, Any]) -> str:
    """
    Decide which KIE API flavor to use.
    - default: jobs/createTask (supports nano-banana models)
    - gpt4o-image: /api/v1/gpt4o-image/generate
    """
    raw = (payload.get("provider") or payload.get("kieProvider") or payload.get("kie_provider") or "").strip().lower()
    model = (payload.get("model") or payload.get("kieModel") or payload.get("kie_model") or "").strip().lower()

    if raw in {"gpt4o-image", "gpt4o_image", "kie_gpt4o_image"}:
        return "kie_gpt4o_image"
    if model in {"gpt4o-image", "gpt4o_image", "gpt-4o", "gpt4o", "4o-image-api", "4o_image_api"}:
        return "kie_gpt4o_image"
    # Default to gpt4o-image as requested.
    return "kie_gpt4o_image"

def _map_to_gpt4o_size(aspect: str) -> str:
    """
    gpt4o-image endpoint only supports: 1:1, 3:2, 2:3.
    Map our UI aspect ratios to the closest supported value.
    """
    a = (aspect or "").strip().lower()
    if a in {"1:1"}:
        return "1:1"
    if a in {"3:2", "4:3", "16:9", "2:1", "5:4"}:
        return "3:2"
    if a in {"2:3", "3:4", "9:16", "4:5"}:
        return "2:3"
    # Default landscape
    return "3:2"


def _load_products() -> List[Dict[str, Any]]:
    path = _base_json_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_gender(product: Dict[str, Any]) -> str:
    title = (product.get("title") or product.get("product_name") or "").lower()
    category = (product.get("category") or "").lower()
    hay = f"{title} {category}"
    if "женск" in hay:
        return "female"
    if "мужск" in hay:
        return "male"
    return "unisex"


def _infer_product_type(product: Dict[str, Any]) -> str:
    title = (product.get("title") or product.get("product_name") or "").lower()
    category = (product.get("category") or "").lower()
    hay = f"{title} {category}"
    if "кружк" in hay or "mug" in hay:
        return "mug"
    # Apparel / wearables
    apparel_markers = [
        "футболк",
        "худи",
        "свитшот",
        "толстовк",
        "рубашк",
        "поло",
        "дождевик",
        "плащ",
        "фартук",
        "куртк",
        "жилет",
        "ветровк",
    ]
    if any(m in hay for m in apparel_markers):
        return "apparel"
    if "кружк" in title or "кружк" in category or "mug" in title:
        return "mug"
    return "other"

def _product_prompt_title(product: Dict[str, Any]) -> str:
    """
    KIE/Gemini usually behaves better with short English product descriptors,
    but we keep the real title as fallback.
    """
    title = str(product.get("title") or "").strip()
    hay = title.lower()
    if "худи" in hay or "hoodie" in hay:
        return "white hoodie"
    if "свитшот" in hay or "sweatshirt" in hay:
        return "white sweatshirt"
    if "толстовк" in hay:
        return "zip hoodie"
    if "поло" in hay:
        return "polo shirt"
    if "рубашк" in hay:
        return "shirt"
    if "футболк" in hay or "t-shirt" in hay or "tshirt" in hay:
        return "white t-shirt"
    if "кружк" in hay or "mug" in hay:
        return "ceramic mug"
    if "бейсболк" in hay or "кепк" in hay:
        return "baseball cap"
    if "панама" in hay:
        return "bucket hat"
    if "бандана" in hay or "платок" in hay:
        return "bandana"
    if "перчатк" in hay:
        return "gloves"
    if "варежк" in hay:
        return "mittens"
    if "шапка" in hay:
        return "beanie"
    if "шарф" in hay:
        return "scarf"
    if "дождевик" in hay or "плащ" in hay:
        return "raincoat"
    if "фартук" in hay:
        return "apron"
    return title or "product"


def _default_product_image(product: Dict[str, Any]) -> Optional[str]:
    images = product.get("images") or product.get("photos") or []
    if isinstance(images, list) and images:
        return images[0]
    return None


def _breadcrumbs_to_category(breadcrumbs: Any) -> str:
    if not breadcrumbs:
        return ""
    if isinstance(breadcrumbs, list):
        parts: list[str] = []
        for b in breadcrumbs:
            if isinstance(b, str):
                parts.append(b.strip())
            elif isinstance(b, dict):
                for key in ("title", "name", "label", "text"):
                    if b.get(key):
                        parts.append(str(b.get(key)).strip())
                        break
        parts = [p for p in parts if p]
        return " / ".join(parts[-3:])
    return str(breadcrumbs)


def _extract_material(specs: Any) -> str:
    if not isinstance(specs, dict):
        return ""
    for key in ("Материал", "Состав", "Материалы", "Ткань", "Fabric", "Material"):
        val = specs.get(key)
        if val:
            return str(val)
    return ""


def _extract_price(variants: Any) -> str:
    if not isinstance(variants, list) or not variants:
        return ""

    def to_num(v: Any) -> Optional[float]:
        if v is None:
            return None
        s = str(v).strip().replace(" ", "").replace("₽", "")
        s = "".join(ch for ch in s if (ch.isdigit() or ch in {".", ","}))
        s = s.replace(",", ".")
        try:
            return float(s) if s else None
        except ValueError:
            return None

    nums: list[float] = []
    for it in variants:
        if not isinstance(it, dict):
            continue
        n = to_num(it.get("price"))
        if n is not None and n > 0:
            nums.append(n)
    if not nums:
        return ""
    m = min(nums)
    if m.is_integer():
        return f"{int(m)} ₽"
    return f"{m:.2f} ₽"


def _extract_article(variants: Any) -> str:
    if not isinstance(variants, list) or not variants:
        return ""
    for it in variants:
        if not isinstance(it, dict):
            continue
        art = (it.get("article") or "").strip()
        if art:
            return art
    return ""


def _normalize_product(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supports two schemas:
      - legacy: {title, url, article, category, images, ...}
      - current gifts.ru scraper: {product_name, product_url, photos, specs, variants, breadcrumbs, ...}
    """
    if "title" in raw or "url" in raw:
        images = raw.get("images") or []
        return {
            "id": raw.get("url") or raw.get("article") or raw.get("title"),
            "title": raw.get("title"),
            "url": raw.get("url"),
            "article": raw.get("article"),
            "material": raw.get("material"),
            "price": raw.get("price"),
            "description": raw.get("description"),
            "category": raw.get("category"),
            "images": images if isinstance(images, list) else [],
        }

    photos = raw.get("photos") or []
    photos_out: list[str] = []
    if isinstance(photos, list):
        for u in photos:
            if not isinstance(u, str):
                continue
            u = u.strip()
            if not u.startswith("http"):
                continue
            if "mc.yandex.ru" in u:
                continue
            photos_out.append(u)

    variants = raw.get("variants")
    url = raw.get("product_url") or ""
    return {
        "id": url or raw.get("product_name"),
        "title": raw.get("product_name"),
        "url": url,
        "article": _extract_article(variants),
        "material": _extract_material(raw.get("specs")),
        "price": _extract_price(variants),
        "description": raw.get("description"),
        "category": _breadcrumbs_to_category(raw.get("breadcrumbs")),
        "images": photos_out,
        "variants": variants if isinstance(variants, list) else [],
    }


def _product_matches_id(raw: Dict[str, Any], product_id: str) -> bool:
    product_id = (product_id or "").strip()
    if not product_id:
        return False
    if raw.get("url") and str(raw.get("url")) == product_id:
        return True
    if raw.get("product_url") and str(raw.get("product_url")) == product_id:
        return True
    if raw.get("article") and str(raw.get("article")) == product_id:
        return True
    if raw.get("variants") and isinstance(raw.get("variants"), list):
        for v in raw["variants"]:
            if isinstance(v, dict) and str(v.get("article") or "") == product_id:
                return True
    return False


@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}

@app.head("/")
async def head_root() -> Response:
    # Render (and other platforms) may probe the service with HEAD /
    # to detect readiness/port binding.
    return Response(status_code=200)

@app.get("/api/public-config")
async def public_config() -> Dict[str, Any]:
    return {
        "externalImageProxyBase": (settings.EXTERNAL_IMAGE_PROXY_BASE or "").strip(),
        "imageProxyEnabled": bool(settings.IMAGE_PROXY_ENABLED),
        "generateAsync": bool(settings.GENERATE_ASYNC),
    }


def _proxy_allowed_hosts() -> set[str]:
    return {h.strip().lower() for h in (settings.IMAGE_PROXY_HOSTS or "").split(",") if h.strip()}


@app.get("/api/image")
async def image_proxy(url: str) -> Response:
    """
    Proxies images from allowed hosts to avoid hotlink restrictions.
    """
    if not settings.IMAGE_PROXY_ENABLED:
        raise HTTPException(status_code=404, detail="image proxy disabled")

    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid url")

    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise HTTPException(status_code=400, detail="invalid url")

    host = parsed.hostname.lower()
    if host not in _proxy_allowed_hosts():
        raise HTTPException(status_code=400, detail=f"host not allowed: {host}")

    upstream_site = f"{parsed.scheme}://{parsed.netloc}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Primerch image proxy)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        # Some CDNs block hotlinking unless a same-site Referer/Origin is present.
        "Referer": upstream_site,
        "Origin": upstream_site.rstrip("/"),
    }

    client = httpx.AsyncClient(timeout=30, follow_redirects=True)
    stream_ctx = client.stream("GET", url, headers=headers)
    try:
        upstream = await stream_ctx.__aenter__()
    except Exception as e:
        # In restricted environments (e.g. PythonAnywhere free) outbound TCP may be blocked.
        # Be defensive here: return a regular 502 instead of letting the exception bubble up.
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"upstream connect failed: {e}") from e

    if upstream.status_code >= 400:
        await stream_ctx.__aexit__(None, None, None)
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"upstream {upstream.status_code}")

    content_type = upstream.headers.get("content-type", "application/octet-stream")

    async def _close() -> None:
        try:
            await stream_ctx.__aexit__(None, None, None)
        finally:
            await client.aclose()

    cache = "public, max-age=3600"
    return StreamingResponse(
        upstream.aiter_bytes(),
        media_type=content_type,
        headers={"Cache-Control": cache},
        background=BackgroundTask(_close),
    )


if settings.DEBUG_ROUTES:
    @app.get("/api/debug/basejson")
    async def debug_basejson() -> Dict[str, Any]:
        path = _base_json_path()
        info: Dict[str, Any] = {
            "python": sys.executable,
            "baseJsonPath": str(path),
            "exists": path.exists(),
            "sizeBytes": path.stat().st_size if path.exists() else 0,
        }
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                info["itemsCount"] = len(data) if isinstance(data, list) else None
                if isinstance(data, list) and data:
                    first = data[0] if isinstance(data[0], dict) else {}
                    info["firstItemKeys"] = sorted(list(first.keys())) if isinstance(first, dict) else []
                    info["firstItemNormalized"] = _normalize_product(first) if isinstance(first, dict) else None
            except Exception as e:
                info["parseError"] = str(e)
        return info


@app.get("/api/products")
async def list_products(
    gender: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 60,
) -> Dict[str, Any]:
    products = _load_products()
    out: List[Dict[str, Any]] = []
    q_norm = (q or "").strip().lower()
    gender_norm = (gender or "").strip().lower()

    for raw in products:
        p = _normalize_product(raw)
        p_gender = _infer_gender(p)
        if gender_norm and gender_norm != "all":
            # Unisex items should be visible for both male/female selections.
            if gender_norm in {"male", "female"}:
                if p_gender not in {gender_norm, "unisex"}:
                    continue
            else:
                if p_gender != gender_norm:
                    continue
        if q_norm:
            hay = f"{p.get('title','')} {p.get('category','')} {p.get('article','')} {p.get('url','')}".lower()
            if q_norm not in hay:
                continue

        out.append(
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "url": p.get("url"),
                "article": p.get("article"),
                "material": p.get("material"),
                "price": p.get("price"),
                "description": p.get("description"),
                "category": p.get("category"),
                "images": p.get("images") or [],
                "gender": p_gender,
                "type": _infer_product_type(p),
            }
        )
        if len(out) >= max(1, min(limit, 200)):
            break
    return {"items": out, "total": len(out)}


@app.post("/api/uploads")
async def upload_image(request: Request, file: UploadFile = File(...)) -> Dict[str, Any]:
    filename, url = await save_upload_image(request, file)
    return {"filename": filename, "url": url, "contentType": file.content_type}


@app.post("/api/generate")
async def generate(
    request: Request,
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Expected payload (minimal):
      - productId OR productArticle: str
      - placement: str
      - application: str
      - scene_mode: on_model | product_only (optional)
      - model_gender: male | female | neutral (optional)
      - logoUrl OR text
    """
    product_id = (payload.get("productId") or "").strip()
    product_article = (payload.get("productArticle") or "").strip()
    placement = (payload.get("placement") or "").strip()
    application = (payload.get("application") or "embroidery").strip()
    image_size = (payload.get("image_size") or payload.get("imageSize") or "4:3").strip()
    resolution = (payload.get("resolution") or "720p").strip()
    num_images = int(payload.get("numImages") or 1)
    scene_mode = (payload.get("scene_mode") or payload.get("sceneMode") or "on_model").strip()
    model_gender = (payload.get("model_gender") or payload.get("modelGender") or "neutral").strip()
    speed_mode = (payload.get("speed_mode") or payload.get("speedMode") or "quality").strip()
    kie_provider = _coerce_provider(payload)
    # Default model is irrelevant for gpt4o-image provider, but keep a sane default for jobs/createTask.
    kie_model = (payload.get("model") or payload.get("kieModel") or payload.get("kie_model") or "nano-banana-2").strip()

    # gpt4o-image has a restricted set of sizes; align prompt + request size.
    prompt_aspect_ratio = image_size
    gpt4o_size = ""
    if kie_provider == "kie_gpt4o_image":
        gpt4o_size = (payload.get("size") or "").strip() or _map_to_gpt4o_size(image_size)
        prompt_aspect_ratio = gpt4o_size

    if not product_id and not product_article:
        raise HTTPException(status_code=400, detail="productId or productArticle is required")
    if not placement:
        raise HTTPException(status_code=400, detail="placement is required")

    products = _load_products()
    lookup = product_id or product_article
    raw_product = next((p for p in products if isinstance(p, dict) and _product_matches_id(p, lookup)), None)
    if not raw_product:
        raise HTTPException(status_code=404, detail="Product not found in base.json (by productId/productArticle)")
    product = _normalize_product(raw_product)

    product_image_url = (payload.get("productImageUrl") or "").strip() or _default_product_image(product)
    if not product_image_url:
        raise HTTPException(status_code=400, detail="productImageUrl missing and product has no images")

    logo_url = (payload.get("logoUrl") or "").strip()
    text_value = (payload.get("text") or "").strip()
    if not logo_url and not text_value:
        raise HTTPException(status_code=400, detail="logoUrl or text is required")

    source_kind = "logo" if logo_url else "text"
    if not logo_url and text_value:
        path = render_text_png(text_value)
        logo_url = build_file_url(request, f"/uploads/{path.name}")

    prompt = build_nanobanana_prompt(
        PromptInputs(
            product_title=_product_prompt_title(product),
            application=application,
            placement=placement,
            aspect_ratio=prompt_aspect_ratio,
            scene_mode=scene_mode,
            model_gender=model_gender,
            source_kind=source_kind,
            source_text=text_value if source_kind == "text" else "",
            speed_mode=speed_mode,
        )
    )

    # Build callback only if PUBLIC_BASE_URL is configured (otherwise polling-only).
    call_back_url = (payload.get("callBackUrl") or "").strip()
    if not call_back_url:
        base = build_file_url(request, "/").rstrip("/")
        # If PUBLIC_BASE_URL is not set, `base` will be localhost and not reachable externally.
        if is_public_http_url(base):
            call_back_url = build_file_url(request, "/api/callback")

    client = get_client()

    def _server_base_url() -> str:
        return build_file_url(request, "/").rstrip("/")

    async def to_kie_file_url(source_url: str, *, server_base: str, upload_path: str = "primerch") -> str:
        if settings.KIE_UPLOAD_CACHE:
            cached = _kie_cache.get(source_url)
            if cached:
                return cached

        # If the URL points to our own /uploads, we can stream-upload without public exposure.
        if source_url.startswith(server_base + "/uploads/"):
            name = source_url.split("/uploads/", 1)[1].split("?", 1)[0]
            local = uploads_dir() / name
            if not local.exists():
                raise HTTPException(status_code=400, detail=f"Upload not found on server: {name}")
            up = await client.file_stream_upload(local, upload_path=upload_path)
            file_url = extract_uploaded_file_url(up)
            if not file_url:
                raise HTTPException(status_code=502, detail=f"KIE file-stream-upload failed: {up}")
            if settings.KIE_UPLOAD_CACHE:
                _kie_cache.set(source_url, str(file_url))
            return str(file_url)

        # Otherwise, require a public URL and use URL-upload.
        if not is_public_http_url(source_url):
            raise HTTPException(
                status_code=400,
                detail=(
                    "productImageUrl/logoUrl must be a PUBLIC http(s) URL (or uploaded via /api/uploads). "
                    f"Got: {source_url}"
                ),
            )
        up = await client.file_url_upload(source_url, upload_path=upload_path)
        file_url = extract_uploaded_file_url(up)
        if not file_url:
            raise HTTPException(status_code=502, detail=f"KIE file-url-upload failed: {up}")
        if settings.KIE_UPLOAD_CACHE:
            _kie_cache.set(source_url, str(file_url))
        return str(file_url)

    def _extract_task_id(create_task_resp: Any) -> str:
        if isinstance(create_task_resp, dict):
            # Some endpoints may return taskId at the top level.
            for k in ("taskId", "task_id", "id"):
                if create_task_resp.get(k):
                    return str(create_task_resp.get(k))
            data = create_task_resp.get("data")
            if isinstance(data, dict):
                tid = data.get("taskId") or data.get("task_id") or data.get("id")
                if tid:
                    return str(tid)
        return ""

    async def _submit_job(job_id: str, server_base: str, job_payload: Dict[str, Any]) -> None:
        job = _jobs.get(job_id)
        if not job:
            return
        job.state = "submitting"
        job.updated_at = time.time()
        job.provider = str(job_payload.get("provider") or job.provider or "kie_gpt4o_image")
        try:
            product_kie_url = await to_kie_file_url(job_payload["productImageUrl"], server_base=server_base)
            logo_kie_url = await to_kie_file_url(job_payload["logoUrl"], server_base=server_base)

            if job.provider == "kie_gpt4o_image":
                kie_payload = {
                    "filesUrl": [product_kie_url, logo_kie_url],
                    "prompt": job_payload["prompt"],
                    "size": job_payload.get("size") or _map_to_gpt4o_size(job_payload.get("image_size") or ""),
                    **({"callBackUrl": job_payload.get("callBackUrl")} if job_payload.get("callBackUrl") else {}),
                    "isEnhance": False,
                    "uploadCn": False,
                    "enableFallback": False,
                    "fallbackModel": "FLUX_MAX",
                }
                res = await client.gpt4o_image_generate(kie_payload)
            else:
                kie_payload = {
                    "model": (job_payload.get("model") or "nano-banana-2"),
                    **({"callBackUrl": job_payload.get("callBackUrl")} if job_payload.get("callBackUrl") else {}),
                    "input": {
                        "prompt": job_payload["prompt"],
                        # KIE payload formats differ by model/version; send both keys for maximum compatibility.
                        "image_input": [product_kie_url, logo_kie_url],
                        "image_urls": [product_kie_url, logo_kie_url],
                        "aspect_ratio": job_payload.get("image_size") or "4:3",
                        "image_size": job_payload.get("image_size") or "4:3",
                        "resolution": job_payload.get("resolution") or "720p",
                        "output_format": job_payload.get("output_format") or "png",
                    },
                }
                res = await client.create_task(kie_payload)
            tid = _extract_task_id(res)
            job.kie_task_id = tid
            job.state = "submitted" if tid else "failed"
            job.error = "" if tid else f"Missing taskId in response: {res}"
            job.request_payload = {"request": kie_payload, "response": res}
            job.updated_at = time.time()
        except Exception as e:
            job.state = "failed"
            job.error = str(e)
            job.updated_at = time.time()

    # Always return quickly (<=30s). Submit to upstream in background.
    if settings.GENERATE_ASYNC:
        job_id = uuid4().hex
        now = time.time()
        job = GenerateJob(job_id=job_id, created_at=now, updated_at=now, state="queued", provider=kie_provider)
        _jobs[job_id] = job

        submit_payload = {
            "prompt": prompt,
            "productImageUrl": product_image_url,
            "logoUrl": logo_url,
            "callBackUrl": call_back_url,
            "image_size": (payload.get("image_size") or payload.get("imageSize") or image_size or "4:3"),
            "resolution": resolution or "720p",
            "output_format": (payload.get("output_format") or payload.get("outputFormat") or "png"),
            "provider": kie_provider,
            "model": kie_model,
            "size": gpt4o_size,
        }
        background_tasks.add_task(_submit_job, job_id, _server_base_url(), submit_payload)
        return {"provider": "kie", "kieProvider": kie_provider, "jobId": job_id, "state": "queued"}

    # Fallback sync mode (not recommended for strict latency).
    product_kie_url = await to_kie_file_url(product_image_url, server_base=_server_base_url())
    logo_kie_url = await to_kie_file_url(logo_url, server_base=_server_base_url())

    if kie_provider == "kie_gpt4o_image":
        kie_payload = {
            "filesUrl": [product_kie_url, logo_kie_url],
            "prompt": prompt,
            "size": gpt4o_size or _map_to_gpt4o_size(image_size),
            **({"callBackUrl": call_back_url} if call_back_url else {}),
            "isEnhance": False,
            "uploadCn": False,
            "enableFallback": False,
            "fallbackModel": "FLUX_MAX",
        }
        res = await client.gpt4o_image_generate(kie_payload)
    else:
        kie_payload = {
            "model": kie_model or "nano-banana-2",
            **({"callBackUrl": call_back_url} if call_back_url else {}),
            "input": {
                "prompt": prompt,
                # KIE payload formats differ by model/version; send both keys for maximum compatibility.
                "image_input": [product_kie_url, logo_kie_url],
                "image_urls": [product_kie_url, logo_kie_url],
                "aspect_ratio": (payload.get("image_size") or payload.get("imageSize") or image_size or "4:3"),
                "image_size": (payload.get("image_size") or payload.get("imageSize") or image_size or "4:3"),
                "resolution": resolution or "720p",
                "output_format": (payload.get("output_format") or payload.get("outputFormat") or "png"),
            },
        }
        res = await client.create_task(kie_payload)

    return {
        "provider": "kie",
        "kieProvider": kie_provider,
        "request": kie_payload,
        "response": res,
        "kieTaskId": _extract_task_id(res),
    }


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str) -> Dict[str, Any]:
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    out: Dict[str, Any] = {
        "jobId": job.job_id,
        "state": job.state,
        "error": job.error,
        "kieProvider": job.provider,
        "kieTaskId": job.kie_task_id or None,
        "createdAt": job.created_at,
        "updatedAt": job.updated_at,
    }

    if job.kie_task_id:
        # Reuse existing task-details logic.
        details = await task_details(job.kie_task_id, provider=job.provider)
        out["task"] = details
    return out


@app.get("/api/tasks/{task_id}")
async def task_details(task_id: str, provider: str = "") -> Dict[str, Any]:
    client = get_client()
    try:
        if (provider or "").strip().lower() in {"kie_gpt4o_image", "gpt4o-image", "gpt4o_image"}:
            res = await client.gpt4o_image_record_info(task_id)
        else:
            res = await client.record_info(task_id)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"KIE error: {e}") from e

    callback = _callback_store.get(task_id)
    data = (res.get("data") or {}) if isinstance(res, dict) else {}
    result = parse_result_json(data.get("resultJson"))
    if result is None:
        urls = extract_result_urls_any(res)
        result = {"resultUrls": urls} if urls else None
    return {"provider": "kie", "kieProvider": provider or "kie_jobs", "recordInfo": res, "result": result, "callback": callback}


@app.post("/api/callback")
async def kie_callback(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    task_id = (body.get("data") or {}).get("taskId") or body.get("taskId") or (body.get("data") or {}).get("id")
    if task_id:
        _callback_store[str(task_id)] = body
    return {"ok": True}


@app.post("/api/callback/nanobanana")
async def legacy_nanobanana_callback(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    return await kie_callback(body)


def _frontend_dir() -> Path:
    return repo_root() / "frontend"


@app.get("/", response_class=HTMLResponse)
async def root() -> HTMLResponse:
    index = _frontend_dir() / "index.html"
    if index.exists():
        return HTMLResponse(index.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


# Static: frontend assets
if _frontend_dir().exists():
    assets_dir = _frontend_dir() / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    app.mount("/static", StaticFiles(directory=str(_frontend_dir()), html=True), name="frontend")

# Static: uploads
app.mount("/uploads", StaticFiles(directory=str(uploads_dir())), name="uploads")
