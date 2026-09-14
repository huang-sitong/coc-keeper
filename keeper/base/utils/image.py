"""图片工具（移植自 LangBot pkg/utils/image.py 中 aiocqhttp 依赖的部分）。"""
from __future__ import annotations

import asyncio
import base64
import io
import ssl
import typing
from urllib.parse import parse_qs, urlparse

import aiohttp
import PIL.Image

from keeper.base.utils import httpclient

_INSECURE_SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
_INSECURE_SSL_CONTEXT.check_hostname = False
_INSECURE_SSL_CONTEXT.verify_mode = ssl.CERT_NONE
DEFAULT_BASE64_MEDIA_LIMIT = 10 * 1024 * 1024


def _detect_image_format(file_bytes: bytes) -> str:
    with PIL.Image.open(io.BytesIO(file_bytes)) as image:
        return str(image.format or "jpeg").lower()


def _decode_base64_limited(value: str, max_bytes: int) -> bytes:
    max_bytes = max(int(max_bytes), 1)
    max_encoded_chars = 4 * ((max_bytes + 2) // 3) + 4
    if len(value) > max_encoded_chars:
        raise ValueError(f"Base64 media exceeds the {max_bytes}-byte limit")
    decoded = base64.b64decode(value)
    if len(decoded) > max_bytes:
        raise ValueError(f"Base64 media exceeds the {max_bytes}-byte limit")
    return decoded


async def decode_base64_limited(
    value: str,
    *,
    max_bytes: int = DEFAULT_BASE64_MEDIA_LIMIT,
) -> bytes:
    return await asyncio.to_thread(_decode_base64_limited, value, max_bytes)


async def encode_base64(data: bytes) -> str:
    return (await asyncio.to_thread(base64.b64encode, data)).decode("utf-8")


def get_qq_image_downloadable_url(image_url: str) -> tuple[str, dict]:
    """获取 QQ 图片的下载链接。"""
    parsed = urlparse(image_url)
    query = parse_qs(parsed.query)
    scheme = parsed.scheme or "http"
    return f"{scheme}://{parsed.netloc}{parsed.path}", query


async def get_qq_image_bytes(
    image_url: str,
    query: dict | None = None,
) -> tuple[bytes, str]:
    """获取 QQ 图片 bytes 与格式。"""
    query = dict(query or {})
    image_url, query_in_url = get_qq_image_downloadable_url(image_url)
    query = {**query, **query_in_url}
    session = httpclient.get_session()
    async with session.get(
        image_url,
        params=query,
        ssl=_INSECURE_SSL_CONTEXT,
        timeout=aiohttp.ClientTimeout(total=30.0),
    ) as resp:
        resp.raise_for_status()
        file_bytes = await httpclient.read_limited(resp)
        content_type = resp.headers.get("Content-Type")
        if not content_type:
            image_format = "jpeg"
        elif not content_type.startswith("image/"):
            image_format = await asyncio.to_thread(_detect_image_format, file_bytes)
        else:
            image_format = content_type.split("/")[-1]
        return file_bytes, image_format


async def qq_image_url_to_base64(image_url: str) -> tuple[str, str]:
    """将 QQ 图片 URL 转为 base64，返回 (base64, 图片格式)。"""
    image_url, query = get_qq_image_downloadable_url(image_url)
    query = {k: v[0] for k, v in query.items()}
    file_bytes, image_format = await get_qq_image_bytes(image_url, query)
    base64_str = await encode_base64(file_bytes)
    return base64_str, image_format
