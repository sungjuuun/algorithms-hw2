import random
import unittest

from experiments.probe_experiment import (
    LOAD_FACTORS,
    generate_keys,
    linear_probing_theory,
    separate_chaining_theory,
    generate_urls,
)


class ProbeExperimentTests(unittest.TestCase):
    def test_url_generation_is_reproducible_and_uses_http_schemes(self):
        first = generate_urls(random.Random(27), 10, "insert")
        second = generate_urls(random.Random(27), 10, "insert")

        self.assertEqual(first, second)
        for url in first:
            with self.subTest(url=url):
                self.assertTrue(url.startswith(("http://", "https://")))

    def test_inserted_and_unsuccessful_keys_are_disjoint(self):
        rng = random.Random(27)
        inserted = generate_urls(rng, 100, "insert")
        unsuccessful = generate_urls(rng, 2000, "missing")

        for url in unsuccessful:
            with self.subTest(url=url):
                self.assertNotIn(url, inserted)

    def test_load_factors_cover_tenth_steps_through_nine_tenths(self):
        self.assertEqual(LOAD_FACTORS, tuple(index / 10 for index in range(1, 10)))

    def test_comparison_keys_are_reproducible_and_namespaced(self):
        first = generate_keys(random.Random(27), 10, "shared")
        second = generate_keys(random.Random(27), 10, "shared")
        missing = generate_keys(random.Random(27), 10, "missing")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 10)
        for key in first:
            self.assertTrue(key.startswith("shared-"))
        for key in missing:
            self.assertTrue(key.startswith("missing-"))

    def test_theoretical_probe_counts_match_standard_formulas(self):
        self.assertEqual(separate_chaining_theory(0.5), (1.25, 0.5))
        for load_factor, expected in (
            (0.5, (1.5, 2.5)),
            (0.8, (3.0, 13.0)),
            (0.9, (5.5, 50.5)),
        ):
            actual = linear_probing_theory(load_factor)
            with self.subTest(load_factor=load_factor):
                self.assertAlmostEqual(actual[0], expected[0])
                self.assertAlmostEqual(actual[1], expected[1])


if __name__ == "__main__":
    unittest.main()
