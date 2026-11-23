import unittest

from src.linear_probing_hash_table import LinearProbingHashTable


class LinearProbingHashTableTests(unittest.TestCase):
    def test_bucket_index_uses_horner_hash(self):
        table = LinearProbingHashTable(M=1000)

        self.assertEqual(table.bucket_index("ab"), 105)

    def test_collision_sequence_wraps_around_and_counts_slots(self):
        table = LinearProbingHashTable(M=3)
        for key in ("a", "d", "g"):
            table.put(key, key.upper())

        self.assertEqual(table.probe_path("g"), (1, 2, 0))
        self.assertEqual(table.get("g"), "G")
        self.assertEqual(table.probe_count("g"), 3)
        self.assertEqual(table.probe_count("j"), 3)
        self.assertNotIn("j", table)
        with self.assertRaises(KeyError):
            table.get("j")

    def test_missing_search_stops_at_first_empty_slot(self):
        table = LinearProbingHashTable(M=5)

        self.assertEqual(table.probe_count("missing"), 1)

    def test_existing_key_can_be_updated_when_table_is_full(self):
        table = LinearProbingHashTable(M=2)
        table.put("first", 1)
        table.put("second", 2)

        table.put("first", "updated")

        self.assertEqual(table.get("first"), "updated")
        self.assertEqual(len(table), 2)
        self.assertEqual(table.load_factor, 1.0)

    def test_new_key_overflow_does_not_change_table(self):
        table = LinearProbingHashTable(M=2)
        table.put("first", 1)
        table.put("second", 2)
        items_before = sorted(table.items())

        with self.assertRaises(OverflowError):
            table.put("third", 3)

        self.assertEqual(sorted(table.items()), items_before)
        self.assertEqual(len(table), 2)

    def test_common_collection_interface(self):
        table = LinearProbingHashTable(M=4)
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

    def test_empty_string_is_a_valid_key(self):
        table = LinearProbingHashTable()
        table.put("", "empty")

        self.assertEqual(table.get(""), "empty")
        self.assertIn("", table)

    def test_missing_key_raises_key_error(self):
        with self.assertRaises(KeyError):
            LinearProbingHashTable().get("missing")

    def test_invalid_sizes_and_non_string_keys_are_rejected(self):
        for size in (0, -1):
            with self.subTest(size=size):
                with self.assertRaises(ValueError):
                    LinearProbingHashTable(M=size)
        for size in (True, "4"):
            with self.subTest(size=size):
                with self.assertRaises(TypeError):
                    LinearProbingHashTable(M=size)

        table = LinearProbingHashTable()
        for operation in (
            lambda: table.bucket_index(1),
            lambda: table.put(1, "value"),
            lambda: table.get(1),
            lambda: table.probe_count(1),
        ):
            with self.subTest(operation=operation):
                with self.assertRaises(TypeError):
                    operation()


if __name__ == "__main__":
    unittest.main()
