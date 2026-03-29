"""Git-based core update support for HyperCore."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class UpdateResult:
    success: bool
    changed: bool
    message: str


class CoreUpdater:
    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path

    def update_core(self) -> UpdateResult:
        inside_repo = self._run_git("rev-parse", "--is-inside-work-tree")
        if inside_repo.returncode != 0:
            return UpdateResult(False, False, self._friendly_error(inside_repo.stderr))

        before_head = self._run_git("rev-parse", "HEAD")
        if before_head.returncode != 0:
            return UpdateResult(False, False, self._friendly_error(before_head.stderr))

        pull_result = self._run_git("pull", "--ff-only")
        if pull_result.returncode != 0:
            return UpdateResult(False, False, self._friendly_error(pull_result.stderr))

        after_head = self._run_git("rev-parse", "HEAD")
        if after_head.returncode != 0:
            return UpdateResult(False, False, self._friendly_error(after_head.stderr))

        changed = before_head.stdout.strip() != after_head.stdout.strip()
        if changed:
            return UpdateResult(True, True, "Core update complete. Restarting.")
        return UpdateResult(True, False, "Core is already up to date.")

    def _run_git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self._root_path,
            capture_output=True,
            text=True,
            shell=False,
        )

    def _friendly_error(self, stderr: str) -> str:
        message = stderr.strip() or "Git command failed."
        if "dubious ownership" in message.lower():
            return (
                "Git blocked the update because this workspace is not marked as a safe "
                "directory in your Git configuration."
            )
        return message


__all__ = ["CoreUpdater", "UpdateResult"]
