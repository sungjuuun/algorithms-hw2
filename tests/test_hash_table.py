import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_bucket_index_uses_horner_hash(self):
        table = HashTable(M=1000)

        self.assertEqual(table.bucket_index("ab"), 105)

    def test_multiple_keys_collide_when_table_size_is_one(self):
        table = HashTable(M=1)
        entries = (("alpha", 1), ("beta", 2), ("gamma", 3))

        for key, value in entries:
            table.put(key, value)

        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)
        self.assertEqual(len(table), 3)

    def test_get_missing_key_raises_key_error(self):
        table = HashTable()

        with self.assertRaises(KeyError):
            table.get("missing")

    def test_put_updates_existing_key_without_increasing_size(self):
        table = HashTable()
        table.put("key", "old")

        table.put("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(len(table), 1)

    def test_empty_string_is_a_valid_key(self):
        table = HashTable()
        table.put("", "empty")

        self.assertEqual(table.get(""), "empty")
        self.assertIn("", table)

    def test_common_collection_interface(self):
        table = HashTable(M=4)
        table.put("alpha", "one")
        table.put("beta", "two")

        self.assertEqual(len(table), 2)
        self.assertIn("alpha", table)
        self.assertNotIn("missing", table)
        self.assertEqual(table.load_factor, 0.5)
        self.assertEqual(
            sorted(table.items()),
            [("alpha", "one"), ("beta", "two")],
        )

        table.put("alpha", "updated")

        self.assertEqual(len(table), 2)
        self.assertEqual(table.load_factor, 0.5)
        self.assertEqual(
            sorted(table.items()),
            [("alpha", "updated"), ("beta", "two")],
        )

    def test_probe_count_measures_successful_and_failed_searches(self):
        table = HashTable(M=1)
        table.put("first", 1)

        self.assertEqual(table.probe_count("first"), 1)

        table.put("second", 2)
        table.put("third", 3)

        self.assertEqual(table.probe_count("missing"), 3)

    def test_invalid_table_sizes_raise_expected_errors(self):
        for size in (0, -1):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    HashTable(M=size)

        for size in (True, "4"):
            with self.subTest(size=size):
                with self.assertRaises(TypeError):
                    HashTable(M=size)

    def test_non_string_keys_raise_type_error(self):
        table = HashTable()

        for operation in (
            lambda: table.bucket_index(1),
            lambda: table.put(1, "value"),
            lambda: table.get(1),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(TypeError):
                    operation()


if __name__ == "__main__":
    unittest.main()
