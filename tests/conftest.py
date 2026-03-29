"""Shared test fixtures."""

import psycopg
import pytest
from psycopg import sql

from vital.config import DATABASE_URL


@pytest.fixture()
def test_db(monkeypatch):
    """Create a clean test schema, run the test, then tear down."""
    schema = f"test_{id(monkeypatch):x}"
    schema_id = sql.Identifier(schema)

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(schema_id))
        conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema_id))

    # Patch _connect to always use the test schema
    from vital.health_store import _connect as original_connect

    def _patched_connect(**kwargs):
        c = original_connect(**kwargs)
        c.execute(sql.SQL("SET search_path TO {}").format(schema_id))
        return c

    monkeypatch.setattr("vital.health_store._connect", _patched_connect)

    from vital.health_store import init_db

    init_db()

    yield schema

    monkeypatch.undo()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(schema_id))
