"""state_db.schema — migration idempotency, schema-version recording,
foreign-key enforcement, and transaction rollback. In-memory SQLite only;
no real file, no data/cache/ access."""
from __future__ import annotations

import sqlite3

import pytest

from src.data_access.state_db import connection, schema


def test_fresh_database_migrates_to_current_version():
    conn = connection.connect_in_memory()
    assert schema.get_schema_version(conn) == 0
    result = schema.migrate(conn)
    assert result == schema.CURRENT_SCHEMA_VERSION
    assert schema.get_schema_version(conn) == schema.CURRENT_SCHEMA_VERSION


def test_migration_is_idempotent_on_an_already_migrated_database():
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    tables_before = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    result = schema.migrate(conn)
    tables_after = {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }
    assert result == schema.CURRENT_SCHEMA_VERSION
    assert tables_before == tables_after  # no duplicate/re-created tables


def test_migration_is_repeatable_many_times_on_a_temp_file_database(tmp_path):
    db_path = tmp_path / "state.db"
    for _ in range(3):
        conn = connection.connect(db_path)
        result = schema.migrate(conn)
        assert result == schema.CURRENT_SCHEMA_VERSION
        conn.close()


def test_all_expected_tables_exist_after_migration():
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert {"schema_version", "filing_events", "candidates", "state_transitions", "resolved_identifiers"} <= tables


def test_no_signals_table_exists():
    # Signals must remain derived, never persisted — see
    # signal_repository.py's own module docstring.
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
    assert not any("signal" in t.lower() for t in tables)


def test_foreign_keys_are_enforced_on_every_connection():
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            """
            INSERT INTO candidates (
                id, source, filing_corp_code, filing_rcept_no, matched_rules_json, confidence, status,
                extraction_state, translation_state, excerpt_quality, version, created_at, updated_at
            ) VALUES ('orphan', 'SEC EDGAR', '9999999999', 'no-such-accession', '[]', 'Low',
                      'Candidate detected', 'Not fetched', 'Not requested', 'Unknown', 1, 'x', 'x')
            """
        )
        conn.commit()


def test_transaction_helper_rolls_back_on_failure_leaving_no_partial_write():
    conn = connection.connect_in_memory()
    schema.migrate(conn)
    conn.execute(
        """
        INSERT INTO filing_events (
            source_name, corp_code, rcept_no, corp_name, stock_code, report_nm, rcept_dt, flr_nm
        ) VALUES ('SEC EDGAR', '0000000001', 'acc-1', 'Test Co', 'TST', '8-K', '2026-01-01', 'Test Co')
        """
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        with connection.transaction(conn):
            # A valid insert followed by an insert that violates the
            # composite primary key — the whole transaction must roll
            # back, including the first, otherwise-valid statement.
            conn.execute(
                """
                INSERT INTO filing_events (
                    source_name, corp_code, rcept_no, corp_name, stock_code, report_nm, rcept_dt, flr_nm
                ) VALUES ('SEC EDGAR', '0000000002', 'acc-2', 'Another Co', 'ANO', '8-K', '2026-01-02', 'Another Co')
                """
            )
            conn.execute(
                """
                INSERT INTO filing_events (
                    source_name, corp_code, rcept_no, corp_name, stock_code, report_nm, rcept_dt, flr_nm
                ) VALUES ('SEC EDGAR', '0000000001', 'acc-1', 'Duplicate PK', 'DUP', '8-K', '2026-01-01', 'Dup')
                """
            )

    count = conn.execute("SELECT COUNT(*) AS n FROM filing_events WHERE corp_code = '0000000002'").fetchone()["n"]
    assert count == 0  # rolled back, not partially applied
