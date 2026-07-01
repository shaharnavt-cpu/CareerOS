"""Structural tests for the Career Knowledge Engine persistence layer."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app import models  # noqa: F401
from app.db import session as session_module
from app.db.base import Base

EXPECTED_TABLES = {
    "users",
    "user_preferences",
    "education",
    "experiences",
    "projects",
    "achievements",
    "skills",
    "skill_links",
    "evidence_items",
    "evidence_links",
}

CANONICAL_SOFT_DELETE_TABLES = {
    "users",
    "education",
    "experiences",
    "projects",
    "achievements",
    "skills",
    "evidence_items",
}

APPEND_ONLY_TABLES = {"skill_links", "evidence_links"}


def test_mappers_and_sprint_two_tables_are_configured() -> None:
    configure_mappers()

    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.parametrize("table_name", sorted(EXPECTED_TABLES - {"users"}))
def test_tenant_owned_tables_require_user_id(table_name: str) -> None:
    user_id = Base.metadata.tables[table_name].c.user_id

    assert user_id.nullable is False
    assert {foreign_key.target_fullname for foreign_key in user_id.foreign_keys} == {
        "users.id"
    }


def test_all_foreign_keys_have_a_leading_index_or_unique_constraint() -> None:
    for table in Base.metadata.tables.values():
        indexed_columns = {
            tuple(column.name for column in index.columns) for index in table.indexes
        }
        indexed_columns.update(
            tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
        )

        for foreign_key in table.foreign_keys:
            assert any(
                columns and columns[0] == foreign_key.parent.name
                for columns in indexed_columns
            ), f"{table.name}.{foreign_key.parent.name} is not indexed"


def test_timestamp_and_soft_delete_policies_match_schema() -> None:
    for name, table in Base.metadata.tables.items():
        assert "created_at" in table.c

        if name in APPEND_ONLY_TABLES:
            assert "updated_at" not in table.c
            assert "deleted_at" not in table.c
        else:
            assert "updated_at" in table.c

        assert ("deleted_at" in table.c) is (name in CANONICAL_SOFT_DELETE_TABLES)


def test_database_dependency_closes_its_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = MagicMock()
    context_manager = MagicMock()
    context_manager.__enter__.return_value = session
    session_factory = MagicMock(return_value=context_manager)
    monkeypatch.setattr(session_module, "SessionLocal", session_factory)

    dependency: Iterator[object] = session_module.get_db()
    assert next(dependency) is session

    with pytest.raises(StopIteration):
        next(dependency)

    context_manager.__exit__.assert_called_once()
