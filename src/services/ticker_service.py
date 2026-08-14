from __future__ import annotations

import sqlite3
from typing import Optional

from src.services import audit_service


def get_ticker(conn: sqlite3.Connection, ticker: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM tickers WHERE ticker = ?", (ticker.upper(),)).fetchone()


def list_tickers(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM tickers ORDER BY ticker ASC").fetchall()


def upsert_ticker(
    conn: sqlite3.Connection,
    ticker: str,
    company_name: str,
    sector: str,
    subtheme: str,
    market_cap_category: str,
    jurisdiction: str = "United States",
    is_mock: bool = True,
) -> None:
    ticker = ticker.upper()
    existing = get_ticker(conn, ticker)
    if existing:
        conn.execute(
            "UPDATE tickers SET company_name = ?, sector = ?, subtheme = ?, market_cap_category = ?, "
            "jurisdiction = ?, is_mock = ? WHERE ticker = ?",
            (company_name, sector, subtheme, market_cap_category, jurisdiction, int(is_mock), ticker),
        )
    else:
        conn.execute(
            "INSERT INTO tickers (ticker, company_name, sector, subtheme, market_cap_category, jurisdiction, is_mock) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ticker, company_name, sector, subtheme, market_cap_category, jurisdiction, int(is_mock)),
        )
        audit_service.log_event(conn, "ticker_added", {"ticker": ticker, "company_name": company_name}, ticker=ticker)


def delete_ticker(conn: sqlite3.Connection, ticker: str) -> None:
    """Removes a ticker and its watchlist record. Research history (briefs,
    snapshots, sources) is intentionally preserved for auditability even
    after a ticker is dropped from the active watchlist."""
    ticker = ticker.upper()
    conn.execute("DELETE FROM watchlist_records WHERE ticker = ?", (ticker,))
    audit_service.log_event(conn, "ticker_removed_from_watchlist", {"ticker": ticker}, ticker=ticker)
