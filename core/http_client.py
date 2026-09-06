"""Shared httpx.AsyncClient factory with Android SSL workarounds.

On Android, Python's ssl module cannot reach the system certificate store,
so httpx (which uses certifi or the default SSL context) fails TLS
handshakes.  This module detects Android at import time and builds an
AsyncClient that disables certificate verification there, while keeping it
enabled on every other platform.

Every module that needs an HTTP client should call ``get_client()`` (or
``get_client_with_headers()`` for per-source custom headers) instead of
creating its own ``httpx.AsyncClient``.
"""

from __future__ import annotations

import ssl
from typing import Optional

import httpx
from kivy.utils import platform

_ANDROID = platform == "android"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _make_ssl_context() -> Optional[ssl.SSLContext]:
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


_ssl_ctx: Optional[ssl.SSLContext] = _make_ssl_context()


def get_client(
    *,
    headers: Optional[dict[str, str]] = None,
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
    return get_client(headers=headers, timeout=timeout, follow_redirects=follow_redirects)
