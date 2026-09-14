"""共享 aiohttp.ClientSession（移植自 LangBot pkg/utils/httpclient.py）。

避免每个请求都重建 SSLContext/TCPConnector。
"""
from __future__ import annotations

import asyncio
import json
import typing

import aiohttp

_sessions: dict[str, aiohttp.ClientSession] = {}
DEFAULT_REMOTE_BODY_LIMIT = 10 * 1024 * 1024


class RemoteResponseTooLargeError(ValueError):
    """远程响应超过内存上限。"""


def get_session(*, trust_env: bool = False) -> aiohttp.ClientSession:
    """获取或创建共享的 aiohttp.ClientSession。"""
    key = f"trust_env={trust_env}"
    session = _sessions.get(key)
    if session is None or session.closed:
        session = aiohttp.ClientSession(
            trust_env=trust_env,
            cookie_jar=aiohttp.DummyCookieJar(),
        )
        _sessions[key] = session
    return session


async def close_all() -> None:
    """关闭所有共享会话，应用退出时调用。"""
    for session in _sessions.values():
        if not session.closed:
            await session.close()
    _sessions.clear()


async def read_limited(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int = DEFAULT_REMOTE_BODY_LIMIT,
) -> bytes:
    """以严格字节上限增量读取响应体。"""
    max_bytes = max(int(max_bytes), 1)
    content_length = response.headers.get("Content-Length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except (TypeError, ValueError):
            declared_size = None
        if declared_size is not None and declared_size > max_bytes:
            raise RemoteResponseTooLargeError(
                f"Remote response exceeds the {max_bytes}-byte limit"
            )

    body = bytearray()
    async for chunk in response.content.iter_chunked(64 * 1024):
        body.extend(chunk)
        if len(body) > max_bytes:
            raise RemoteResponseTooLargeError(
                f"Remote response exceeds the {max_bytes}-byte limit"
            )
    return bytes(body)


async def read_text_limited(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int = DEFAULT_REMOTE_BODY_LIMIT,
) -> str:
    body = await read_limited(response, max_bytes=max_bytes)
    return body.decode(response.charset or "utf-8", errors="replace")


async def read_json_limited(
    response: aiohttp.ClientResponse,
    *,
    max_bytes: int = DEFAULT_REMOTE_BODY_LIMIT,
) -> typing.Any:
    body = await read_limited(response, max_bytes=max_bytes)
    return await asyncio.to_thread(json.loads, body)
