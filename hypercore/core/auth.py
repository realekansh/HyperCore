"""Authorization policy services for HyperCore."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hypercore.core.commands import CommandAccess

if TYPE_CHECKING:
    from hypercore.core.kernel import HyperCoreKernel


class AuthorizationService:
    def __init__(self, core: "HyperCoreKernel") -> None:
        self._core = core

    async def is_authorized(self, sender_id: int, access: CommandAccess) -> bool:
        if self._core.owner_id is not None and sender_id == self._core.owner_id:
            return True
        if access is CommandAccess.OWNER:
            return False
        return await self._core.store.is_sudo(sender_id)


__all__ = ["AuthorizationService"]
