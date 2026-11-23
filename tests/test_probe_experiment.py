import random
import unittest

from experiments.probe_experiment import generate_urls


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


if __name__ == "__main__":
    unittest.main()
