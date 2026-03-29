"""Single-instance runtime guard for HyperCore."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO


class InstanceGuard:
    def __init__(self, root_path: Path, *, lock_name: str = "hypercore.lock") -> None:
        self._lock_path = (root_path / "runtime" / lock_name).resolve()
        self._handle: TextIO | None = None

    def acquire(self, runtime_mode: str) -> None:
        if self._handle is not None:
            return

        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self._lock_path.open("a+", encoding="utf-8")
        try:
            self._lock_file(handle)
            handle.seek(0)
            handle.truncate()
            handle.write(
                "\n".join(
                    [
                        f"pid={os.getpid()}",
                        f"runtime={runtime_mode}",
                        f"started_at={datetime.now(timezone.utc).isoformat()}",
                    ]
                )
            )
            handle.flush()
            self._handle = handle
        except Exception:
            handle.close()
            raise

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            self._unlock_file(self._handle)
        finally:
            self._handle.close()
            self._handle = None

    def _lock_file(self, handle: TextIO) -> None:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                if not handle.read(1):
                    handle.write("0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                return

            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another HyperCore instance is already running.") from exc

    def _unlock_file(self, handle: TextIO) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            return

        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


__all__ = ["InstanceGuard"]
