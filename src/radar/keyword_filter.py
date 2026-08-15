"""Cheap, zero-cost pre-filter applied before any LLM call.

Purpose is purely cost control (guardrail principle #10): narrow a feed's raw
items down to plausibly-relevant candidates before spending a Haiku call on
each one. This is intentionally permissive — false positives just cost an
extra cheap LLM call; false negatives silently drop a real finding. The LLM
relevance check in llm_tagger.py is the real, precise gate.
"""
from __future__ import annotations

import re

from src.radar.models import Niche

# Deliberately broad synonym lists per niche. A feed's own niche tag (see
# feeds.py) already scopes most items; this keyword pass is a second check
# so an off-topic story on an otherwise-relevant feed (e.g. a Data Center
# Dynamics story about office real estate) doesn't burn an LLM call.
_KEYWORDS: dict[str, list[str]] = {
    Niche.AI_BUILDOUT.value: [
        "ai ", "artificial intelligence", "data center", "datacenter", "gpu", "accelerator",
        "hyperscaler", "compute cluster", "training cluster", "inference", "chip", "semiconductor",
        "foundry", "hbm", "memory chip", "power grid", "cooling", "capex", "nvidia", "tpu",
    ],
    Niche.HUMANOIDS.value: [
        "humanoid", "robot", "robotics", "actuator", "bipedal", "android", "automation",
        "manufacturing robot", "warehouse robot",
    ],
    Niche.SPACE.value: [
        "space", "satellite", "rocket", "launch", "orbit", "spacecraft", "nasa", "spacex",
        "constellation", "lunar", "mars", "starship",
    ],
    Niche.MACRO.value: [
        "interest rate", "rate cut", "rate hike", "inflation", "cpi", "fomc", "federal reserve",
        "central bank", "ecb", "monetary policy", "fiscal policy", "tariff", "gdp", "jobs report",
        "unemployment", "yield", "treasury", "recession", "basis point",
        "export control", "export administration", "entity list", "denied person", "commerce control list",
        "export ban", "export restriction", "sanction", "bis rule", "section 232",
    ],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    niche: [re.compile(re.escape(kw), re.IGNORECASE) for kw in kws] for niche, kws in _KEYWORDS.items()
}


def is_plausibly_relevant(niche: str, title: str, summary: str) -> bool:
    """True if the item's title/summary contains at least one keyword for
    its feed's declared niche."""
    patterns = _COMPILED.get(niche)
    if not patterns:
        return False
    haystack = f"{title} {summary}"
    return any(p.search(haystack) for p in patterns)
