#!/usr/bin/env python3
"""CLI entrypoint for one Radar scan run — invoked by
.github/workflows/radar_scan.yml on a schedule. Exits non-zero only when the
run produced zero output AND errors (a total failure); partial errors on
individual feeds/items are logged in the run record but don't fail the job,
since one bad feed shouldn't block everything else from being scanned.

Run manually with:  python -m scripts.run_radar_scan
"""
from __future__ import annotations

import sys

from src.radar.scan import run


def main() -> int:
    record = run()
    print(f"Radar scan finished: status={record.status}")
    print(f"  feeds checked:        {record.feeds_checked}")
    print(f"  items seen:           {record.items_seen}")
    print(f"  after keyword filter: {record.items_after_keyword_filter}")
    print(f"  sent to LLM:          {record.items_sent_to_llm}")
    print(f"  saved:                {record.items_saved}")
    print(f"  rejected by guardrail:{record.items_rejected_by_guardrail}")
    if record.errors:
        print(f"  errors ({len(record.errors)}):")
        for e in record.errors:
            print(f"    - {e}")

    if record.status == "error":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
