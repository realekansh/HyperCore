import tempfile
import unittest
from pathlib import Path

from hypercore.core.storage import MemoryStateStore, SQLiteStateStore, create_state_store


class StateStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_state_store_returns_memory_backend_when_url_is_empty(self) -> None:
        store = create_state_store(None, Path.cwd())

        self.assertIsInstance(store, MemoryStateStore)
        self.assertEqual(store.mode, "memory")

    async def test_memory_state_store_tracks_sudo_users(self) -> None:
        store = MemoryStateStore()

        self.assertTrue(await store.add_sudo(1001))
        self.assertFalse(await store.add_sudo(1001))
        self.assertTrue(await store.is_sudo(1001))
        self.assertEqual(await store.list_sudos(), [1001])
        self.assertEqual(await store.count_sudos(), 1)
        self.assertTrue(await store.remove_sudo(1001))
        self.assertFalse(await store.is_sudo(1001))

    async def test_sqlite_state_store_persists_state_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_path = Path(temp_dir)
            database_url = "sqlite:///data/hypercore.db"

            first_store = create_state_store(database_url, root_path)
            self.assertIsInstance(first_store, SQLiteStateStore)
            await first_store.initialize()
            await first_store.add_sudo(2001)
            await first_store.close()

            second_store = create_state_store(database_url, root_path)
            await second_store.initialize()
            self.assertTrue(await second_store.is_sudo(2001))
            self.assertEqual(await second_store.list_sudos(), [2001])
            await second_store.close()

    async def test_invalid_database_url_raises_value_error(self) -> None:
        store = create_state_store("postgresql://example.invalid/hypercore", Path.cwd())

        with self.assertRaises(ValueError):
            await store.initialize()
