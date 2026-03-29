"""Storage contracts and backend implementations for HyperCore."""

from __future__ import annotations

import asyncio
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path


class StateStore(ABC):
    def __init__(self, mode: str) -> None:
        self.mode = mode

    async def initialize(self) -> None:
        """Prepare the backend for use."""

    @abstractmethod
    async def add_sudo(self, user_id: int) -> bool:
        """Add a sudo user. Returns True when the user was newly added."""

    @abstractmethod
    async def remove_sudo(self, user_id: int) -> bool:
        """Remove a sudo user. Returns True when the user existed."""

    @abstractmethod
    async def list_sudos(self) -> list[int]:
        """Return all configured sudo users."""

    async def count_sudos(self) -> int:
        return len(await self.list_sudos())

    @abstractmethod
    async def is_sudo(self, user_id: int) -> bool:
        """Return True when the given user has sudo access."""

    async def close(self) -> None:
        """Release backend resources."""


class MemoryStateStore(StateStore):
    def __init__(self) -> None:
        super().__init__(mode="memory")
        self._lock = asyncio.Lock()
        self._sudo_users: set[int] = set()

    async def add_sudo(self, user_id: int) -> bool:
        async with self._lock:
            if user_id in self._sudo_users:
                return False
            self._sudo_users.add(user_id)
            return True

    async def remove_sudo(self, user_id: int) -> bool:
        async with self._lock:
            if user_id not in self._sudo_users:
                return False
            self._sudo_users.remove(user_id)
            return True

    async def list_sudos(self) -> list[int]:
        async with self._lock:
            return sorted(self._sudo_users)

    async def is_sudo(self, user_id: int) -> bool:
        async with self._lock:
            return user_id in self._sudo_users


class SQLiteStateStore(StateStore):
    def __init__(self, database_url: str, root_path: Path) -> None:
        super().__init__(mode="sqlite")
        self._database_url = database_url
        self._root_path = root_path
        self._lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    async def initialize(self) -> None:
        connect_target = _resolve_sqlite_target(self._database_url, self._root_path)
        if connect_target != ":memory:":
            Path(connect_target).parent.mkdir(parents=True, exist_ok=True)

        self._connection = sqlite3.connect(connect_target, check_same_thread=False)
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS sudo_users ("
            "user_id INTEGER PRIMARY KEY, added_at TEXT NOT NULL)"
        )
        self._connection.commit()

    async def add_sudo(self, user_id: int) -> bool:
        connection = self._require_connection()
        async with self._lock:
            cursor = connection.execute(
                "INSERT OR IGNORE INTO sudo_users (user_id, added_at) VALUES (?, ?)",
                (user_id, datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()
            return cursor.rowcount > 0

    async def remove_sudo(self, user_id: int) -> bool:
        connection = self._require_connection()
        async with self._lock:
            cursor = connection.execute(
                "DELETE FROM sudo_users WHERE user_id = ?",
                (user_id,),
            )
            connection.commit()
            return cursor.rowcount > 0

    async def list_sudos(self) -> list[int]:
        connection = self._require_connection()
        async with self._lock:
            rows = connection.execute(
                "SELECT user_id FROM sudo_users ORDER BY user_id ASC"
            ).fetchall()
            return [int(row[0]) for row in rows]

    async def is_sudo(self, user_id: int) -> bool:
        connection = self._require_connection()
        async with self._lock:
            row = connection.execute(
                "SELECT 1 FROM sudo_users WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row is not None

    async def close(self) -> None:
        async with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("State store is not initialized.")
        return self._connection


def create_state_store(database_url: str | None, root_path: Path) -> StateStore:
    if database_url is None or not database_url.strip():
        return MemoryStateStore()
    return SQLiteStateStore(database_url=database_url, root_path=root_path)


def _resolve_sqlite_target(database_url: str, root_path: Path) -> str:
    value = database_url.strip()
    if value in {":memory:", "sqlite:///:memory:"}:
        return ":memory:"

    if value.startswith("sqlite:///"):
        path = Path(value.removeprefix("sqlite:///"))
    elif "://" in value:
        raise ValueError(
            "Only sqlite:/// DATABASE_URL values are supported in V0.3.0."
        )
    else:
        path = Path(value)

    if path.is_absolute():
        return str(path)
    return str((root_path / path).resolve())


__all__ = [
    "MemoryStateStore",
    "SQLiteStateStore",
    "StateStore",
    "create_state_store",
]
