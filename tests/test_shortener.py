import unittest

from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    def make_shortener(self):
        return URLShortener()

    def test_first_url_receives_code_zero(self):
        shortener = self.make_shortener()

        self.assertEqual(shortener.shorten("https://example.com/first"), "0")

    def test_repeated_url_receives_the_same_code(self):
        shortener = self.make_shortener()
        url = "https://example.com/repeated"

        first_code = shortener.shorten(url)

        self.assertEqual(shortener.shorten(url), first_code)

    def test_different_urls_receive_unique_codes(self):
        shortener = self.make_shortener()

        first_code = shortener.shorten("https://example.com/one")
        second_code = shortener.shorten("https://example.com/two")

        self.assertEqual(first_code, "0")
        self.assertEqual(second_code, "1")
        self.assertNotEqual(first_code, second_code)

    def test_expand_restores_original_url(self):
        shortener = self.make_shortener()
        urls = (
            "http://example.com/",
            "https://example.com/path?query=value",
        )

        for url in urls:
            with self.subTest(url=url):
                code = shortener.shorten(url)
                self.assertEqual(shortener.expand(code), url)

    def test_invalid_urls_raise_value_error(self):
        shortener = self.make_shortener()
        invalid_urls = (
            "",
            "relative/path",
            "ftp://example.com/file",
            "https://example.com/has space",
            "https://example.com:0/",
            "https://example.com:65536/",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_url_without_host_raises_value_error(self):
        shortener = self.make_shortener()

        with self.assertRaises(ValueError):
            shortener.shorten("https:///path")

    def test_non_string_url_raises_type_error(self):
        shortener = self.make_shortener()

        with self.assertRaises(TypeError):
            shortener.shorten(None)

    def test_control_characters_in_url_raise_value_error(self):
        shortener = self.make_shortener()
        urls = (
            "https://example.com/line\nbreak",
            "https://example.com/tab\tvalue",
        )

        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_url_length_boundary(self):
        shortener = self.make_shortener()
        prefix = "https://example.com/"
        url_2048 = prefix + "a" * (2048 - len(prefix))
        url_2049 = prefix + "a" * (2049 - len(prefix))

        self.assertEqual(len(url_2048), 2048)
        self.assertEqual(len(shortener.shorten(url_2048)), 1)
        with self.assertRaises(ValueError):
            shortener.shorten(url_2049)

    def test_expand_distinguishes_unknown_and_noncanonical_codes(self):
        shortener = self.make_shortener()

        with self.assertRaises(KeyError):
            shortener.expand("z")

        for code in ("", "!", "00"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    shortener.expand(code)

    def test_expand_rejects_non_string_codes(self):
        shortener = self.make_shortener()

        for code in (None, 123):
            with self.subTest(code=code):
                with self.assertRaises(TypeError):
                    shortener.expand(code)

    def test_invalid_url_does_not_consume_first_code(self):
        shortener = self.make_shortener()

        with self.assertRaises(ValueError):
            shortener.shorten("ftp://example.com/file")

        self.assertEqual(shortener.shorten("https://example.com/valid"), "0")

    def test_existing_url_behaves_the_same_with_both_strategies(self):
        for strategy in ("chaining", "linear_probing"):
            with self.subTest(strategy=strategy):
                shortener = URLShortener(strategy=strategy)
                url = "https://example.com/same"

                first_code = shortener.shorten(url)

                self.assertEqual(first_code, "0")
                self.assertEqual(shortener.shorten(url), first_code)
                self.assertEqual(shortener.expand(first_code), url)
                self.assertEqual(len(shortener._url_to_code), 1)
                self.assertEqual(len(shortener._code_to_url), 1)

    def test_linear_probing_overflow_preserves_both_tables_and_next_id(self):
        shortener = URLShortener(strategy="linear_probing", table_size=2)
        shortener.shorten("https://example.com/one")
        shortener.shorten("https://example.com/two")
        before_url_items = sorted(shortener._url_to_code.items())
        before_code_items = sorted(shortener._code_to_url.items())

        with self.assertRaises(OverflowError):
            shortener.shorten("https://example.com/three")

        self.assertEqual(sorted(shortener._url_to_code.items()), before_url_items)
        self.assertEqual(sorted(shortener._code_to_url.items()), before_code_items)
        self.assertEqual(shortener._next_id, 2)
        self.assertEqual(len(shortener._url_to_code), 2)
        self.assertEqual(len(shortener._code_to_url), 2)

    def test_reverse_table_overflow_does_not_partially_insert_or_consume_id(self):
        shortener = URLShortener(strategy="linear_probing", table_size=2)
        shortener._code_to_url.put("reserved-1", "one")
        shortener._code_to_url.put("reserved-2", "two")
        before_code_items = sorted(shortener._code_to_url.items())

        with self.assertRaises(OverflowError):
            shortener.shorten("https://example.com/new")

        self.assertEqual(list(shortener._url_to_code.items()), [])
        self.assertEqual(sorted(shortener._code_to_url.items()), before_code_items)
        self.assertEqual(shortener._next_id, 0)


class LinearProbingURLShortenerTests(URLShortenerTests):
    def make_shortener(self):
        return URLShortener(strategy="linear_probing")


if __name__ == "__main__":
    unittest.main()
