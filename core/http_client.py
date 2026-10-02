"""Shared httpx.AsyncClient factory with Android SSL workarounds.

On Android, Python's ssl module cannot reach the system certificate store,
so httpx (which uses certifi or the default SSL context) fails TLS
handshakes.  This module detects Android at import time and builds an
AsyncClient that disables certificate verification there, while keeping it
enabled on every other platform.

Every module that needs an HTTP client should call ``get_client()`` (or
``get_client_with_headers()`` for per-source custom headers) instead of
creating its own ``httpx.AsyncClient``.

This module also owns the two helpers every source shares: HTML parsing
(``parse_html``/``fetch_soup``) and user-facing error wording
(``describe_error``).
"""

from __future__ import annotations

import asyncio
import ssl
from typing import Any

import httpx
from bs4 import BeautifulSoup


def _is_android() -> bool:
    try:
        from kivy.utils import platform

        return platform == "android"
    except Exception:
        return False


_ANDROID = _is_android()

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _make_ssl_context() -> ssl.SSLContext | None:
    """Return an SSL context suitable for the current platform.

    On Android the system CA bundle is not reachable from Python, so we
    create a permissive context that skips certificate verification.
    On desktop platforms we return None so httpx uses its own default
    (which verifies certificates via certifi).
    """
    if not _ANDROID:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_ssl_ctx: ssl.SSLContext | None = _make_ssl_context()


def get_client(
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Create an ``httpx.AsyncClient`` with Android-aware SSL settings.

    Parameters
    ----------
    headers:
        Extra headers merged on top of the sensible defaults.
    timeout:
        Request timeout in seconds.
    follow_redirects:
        Whether to follow HTTP redirects.
    """
    merged = dict(_DEFAULT_HEADERS)
    if headers:
        merged.update(headers)
    return httpx.AsyncClient(
        headers=merged,
        follow_redirects=follow_redirects,
        timeout=timeout,
        # On Android the system CA store is unreachable; disable
        # verification so TLS handshakes succeed.  On desktop the
        # ssl_ctx is None and httpx verifies via certifi as usual.
        verify=_ssl_ctx if _ssl_ctx is not None else True,
    )


def get_client_with_headers(
    headers: dict[str, str],
    *,
    timeout: int = 30,
    follow_redirects: bool = True,
) -> httpx.AsyncClient:
    """Convenience wrapper for sources that supply their own headers.

    The provided *headers* override the defaults (e.g. a custom Referer).
    """
    return get_client(
        headers=headers, timeout=timeout, follow_redirects=follow_redirects
    )


# --------------------------------------------------------------------------
# HTML parsing
# --------------------------------------------------------------------------


def _detect_parser() -> str:
    """Return the fastest bs4 tree builder available on this machine.

    lxml parses roughly 1.6x faster than the pure-Python html.parser and
    releases the GIL while doing so, but it is a compiled extension that the
    Android APK does not bundle (see buildozer.spec).  Probe bs4 itself
    rather than ``import lxml`` so a broken native library also falls back
    instead of crashing on the first fetch.
    """
    for name in ("lxml", "html.parser"):
        try:
            BeautifulSoup("", name)
        except Exception:
            continue
        return name
    return "html.parser"


HTML_PARSER: str = _detect_parser()


async def parse_html(markup: str) -> BeautifulSoup:
    """Parse HTML off the event loop and return a ``BeautifulSoup``."""
    return await asyncio.to_thread(BeautifulSoup, markup, HTML_PARSER)


# Transient statuses worth retrying.  404/403 and friends are deliberately
# absent: retrying a removed novel or an anti-bot block only wastes the
# user's time and makes the rate limiting worse.
_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3
# Cap on a server-supplied Retry-After.  The GUI wraps most of these calls in
# async_loop.run(..., timeout=30), so a large value would eat the whole budget
# and surface as a timeout instead of a rate-limit message.
_MAX_RETRY_AFTER = 8.0
# Used when the server sends no usable Retry-After.
_RETRY_BACKOFF = (1.0, 2.0)


async def _sleep(seconds: float) -> None:
    """Pause between retries.  Tests monkeypatch this to stay instant."""
    await asyncio.sleep(seconds)


def _retry_delay(response: httpx.Response, attempt: int) -> float:
    """Seconds to wait before retrying *response* on attempt *attempt*.

    A sane server-supplied ``Retry-After`` wins; anything larger is clamped to
    the cap rather than honoured, and a missing or non-numeric one falls back
    to exponential backoff.
    """
    try:
        seconds = float(response.headers.get("Retry-After", ""))
    except (TypeError, ValueError):
        seconds = 0.0
    if seconds > 0:
        return min(seconds, _MAX_RETRY_AFTER)
    index = attempt - 1
    return _RETRY_BACKOFF[index] if index < len(_RETRY_BACKOFF) else _RETRY_BACKOFF[-1]


async def _get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """GET *url*, retrying transient statuses, and return the response.

    Raises via ``response.raise_for_status()`` for whatever is still non-2xx
    once the attempts are spent.
    """
    response = await client.get(url, params=params, headers=headers)
    for attempt in range(1, _MAX_ATTEMPTS):
        if response.status_code not in _RETRY_STATUSES:
            break
        await _sleep(_retry_delay(response, attempt))
        response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response


async def fetch_soup(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> BeautifulSoup:
    """GET *url*, raise on a non-2xx status, and parse the body off-loop.

    Transient statuses are retried with backoff: novelfire rate-limits bursty
    chapter paging, and without this every 429/500 became a dead end for the
    caller.  Non-transient failures still raise on the first attempt.
    """
    response = await _get_with_retry(client, url, params=params, headers=headers)
    return await parse_html(response.text)


# --------------------------------------------------------------------------
# User-facing error wording
# --------------------------------------------------------------------------


def _status_code(error: BaseException) -> int | None:
    """Best-effort status code from an HTTP exception.

    Works for ``httpx.HTTPStatusError`` and, because it reads ``.response``
    structurally, for ``curl_cffi.requests.exceptions.HTTPError`` too — so
    this module never has to import curl_cffi (which Android lacks).
    """
    response = getattr(error, "response", None)
    code = getattr(response, "status_code", None)
    return code if isinstance(code, int) else None


def describe_error(error: BaseException, action: str) -> str:
    """Turn an exception into a short user-facing message.

    *action* is what the caller was doing, e.g. ``"Search failed"`` or
    ``"Failed to fetch chapters"``.  Only genuine network failures are
    described as a connection problem; anything else is named instead, so
    a bug in the app never masquerades as "check your connection".
    """
    status = _status_code(error)
    if status is not None:
        if status == 404:
            detail = "page not found (404)"
        elif status == 403:
            detail = "access denied (403)"
        elif status == 429:
            detail = "rate limited (429) — wait a moment and retry"
        elif 500 <= status < 600:
            detail = f"server error ({status}) — try again later"
        else:
            detail = f"HTTP {status}"
        return f"{action} — {detail}."
    if isinstance(error, httpx.TimeoutException):
        return f"{action} — timed out. Check your connection."
    if isinstance(error, httpx.TransportError):
        return f"{action} — could not reach the server."
    return f"{action} — unexpected error ({type(error).__name__})."
