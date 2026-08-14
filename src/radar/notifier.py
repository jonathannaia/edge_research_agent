"""Optional webhook notification for new Radar findings, sent once per scan
run as a single digest (not one message per finding).

Inactive by default — does nothing unless EDGE_RADAR_WEBHOOK_URL is set.
Nobody but the user can create the Slack/Discord/etc. webhook this posts
to, so this ships as ready-to-activate infrastructure, not something wired
up automatically.

Honesty note on scope: this notifies on every new finding from the run,
NOT filtered to tickers on your Watchlist. That filtering isn't possible
from here — this code runs in GitHub Actions, which only has the checked-
out repo; your Watchlist lives in data/edge_research.db, a local SQLite
file that's gitignored and never committed (see .gitignore), so the
scheduled scan has no way to see it. If you want watchlist-filtered
alerts, the honest path is polling data/radar_findings.json client-side
(e.g. from the Streamlit app, which *does* have your watchlist) rather
than from this job.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from src.radar.models import RadarFinding
from src.utils.ssl_context import SSL_CONTEXT

MAX_FINDINGS_IN_MESSAGE = 10


def _format_message(new_findings: list[RadarFinding]) -> str:
    lines = [f"Radar found {len(new_findings)} new item(s) this scan:"]
    for f in new_findings[:MAX_FINDINGS_IN_MESSAGE]:
        tickers = ", ".join(t.ticker for t in f.tickers) or "no ticker"
        lines.append(f"• [{f.niche}] {f.headline} ({tickers}) — {f.source_url}")
    remainder = len(new_findings) - MAX_FINDINGS_IN_MESSAGE
    if remainder > 0:
        lines.append(f"...and {remainder} more.")
    return "\n".join(lines)


def send_webhook_notification(new_findings: list[RadarFinding]) -> str | None:
    """Posts a digest of this run's new findings to EDGE_RADAR_WEBHOOK_URL.
    No-ops silently if the env var isn't set or there's nothing new. Never
    raises — returns an error string on failure so the caller can log it,
    since a broken webhook must never fail the scan itself."""
    url = os.getenv("EDGE_RADAR_WEBHOOK_URL")
    if not url or not new_findings:
        return None

    message = _format_message(new_findings)
    # Sent under both keys so this works unmodified against Slack/Mattermost
    # incoming webhooks (which read "text") and Discord webhooks (which
    # read "content") — receivers ignore fields they don't recognize.
    payload = json.dumps({"text": message, "content": message}).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10, context=SSL_CONTEXT) as resp:
            if resp.status >= 300:
                return f"Webhook returned HTTP {resp.status}"
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        return f"Webhook request failed: {exc}"

    return None
