import unittest

from hypercore.core.auth import AuthorizationService
from hypercore.core.commands import CommandAccess


class _DummyStore:
    def __init__(self, sudo_users: tuple[int, ...] = ()) -> None:
        self._sudo_users = set(sudo_users)

    async def is_sudo(self, user_id: int) -> bool:
        return user_id in self._sudo_users


class _DummyCore:
    def __init__(self, owner_id: int | None, sudo_users: tuple[int, ...] = ()) -> None:
        self.owner_id = owner_id
        self.store = _DummyStore(sudo_users=sudo_users)


class AuthorizationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_owner_is_always_authorized(self) -> None:
        service = AuthorizationService(_DummyCore(owner_id=99))

        self.assertTrue(await service.is_authorized(99, CommandAccess.OWNER))
        self.assertTrue(await service.is_authorized(99, CommandAccess.SUDO))

    async def test_sudo_access_uses_store_for_non_owner(self) -> None:
        service = AuthorizationService(_DummyCore(owner_id=1, sudo_users=(42,)))

        self.assertTrue(await service.is_authorized(42, CommandAccess.SUDO))
        self.assertFalse(await service.is_authorized(7, CommandAccess.SUDO))

    async def test_owner_only_commands_reject_non_owner(self) -> None:
        service = AuthorizationService(_DummyCore(owner_id=1, sudo_users=(42,)))

        self.assertFalse(await service.is_authorized(42, CommandAccess.OWNER))
