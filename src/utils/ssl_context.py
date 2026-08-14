"""Shared HTTPS SSL context using certifi's CA bundle.

Some Python installs (notably python.org builds on macOS) don't wire up a
usable CA trust store for `ssl`/`urllib` by default, causing
CERTIFICATE_VERIFY_FAILED on otherwise-valid HTTPS requests — a real bug
Radar's SEC EDGAR full-text search hit locally during development (see git
history). Anything in this app making a raw HTTPS request outside of
`streamlit`/`anthropic`'s own clients (which handle this themselves) should
use this context: src/providers/edgar_client.py and src/radar/feeds.py
(feedparser's request handler) both do.
"""
from __future__ import annotations

import ssl

try:
    import certifi

    SSL_CONTEXT: ssl.SSLContext | None = ssl.create_default_context(cafile=certifi.where())
except ImportError:  # pragma: no cover - certifi is a listed dependency
    SSL_CONTEXT = None
