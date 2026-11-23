import unittest

from src.shortener import URLShortener


class URLShortenerTests(unittest.TestCase):
    def test_first_url_receives_code_zero(self):
        shortener = URLShortener()

        self.assertEqual(shortener.shorten("https://example.com/first"), "0")

    def test_repeated_url_receives_the_same_code(self):
        shortener = URLShortener()
        url = "https://example.com/repeated"

        first_code = shortener.shorten(url)

        self.assertEqual(shortener.shorten(url), first_code)

    def test_different_urls_receive_unique_codes(self):
        shortener = URLShortener()

        first_code = shortener.shorten("https://example.com/one")
        second_code = shortener.shorten("https://example.com/two")

        self.assertEqual(first_code, "0")
        self.assertEqual(second_code, "1")
        self.assertNotEqual(first_code, second_code)

    def test_expand_restores_original_url(self):
        shortener = URLShortener()
        urls = (
            "http://example.com/",
            "https://example.com/path?query=value",
        )

        for url in urls:
            with self.subTest(url=url):
                code = shortener.shorten(url)
                self.assertEqual(shortener.expand(code), url)

    def test_invalid_urls_raise_value_error(self):
        shortener = URLShortener()
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
        shortener = URLShortener()

        with self.assertRaises(ValueError):
            shortener.shorten("https:///path")

    def test_non_string_url_raises_type_error(self):
        shortener = URLShortener()

        with self.assertRaises(TypeError):
            shortener.shorten(None)

    def test_control_characters_in_url_raise_value_error(self):
        shortener = URLShortener()
        urls = (
            "https://example.com/line\nbreak",
            "https://example.com/tab\tvalue",
        )

        for url in urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    shortener.shorten(url)

    def test_url_length_boundary(self):
        shortener = URLShortener()
        prefix = "https://example.com/"
        url_2048 = prefix + "a" * (2048 - len(prefix))
        url_2049 = prefix + "a" * (2049 - len(prefix))

        self.assertEqual(len(url_2048), 2048)
        self.assertEqual(len(shortener.shorten(url_2048)), 1)
        with self.assertRaises(ValueError):
            shortener.shorten(url_2049)

    def test_expand_distinguishes_unknown_and_noncanonical_codes(self):
        shortener = URLShortener()

        with self.assertRaises(KeyError):
            shortener.expand("z")

        for code in ("", "!", "00"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    shortener.expand(code)

    def test_expand_rejects_non_string_codes(self):
        shortener = URLShortener()

        for code in (None, 123):
            with self.subTest(code=code):
                with self.assertRaises(TypeError):
                    shortener.expand(code)

    def test_invalid_url_does_not_consume_first_code(self):
        shortener = URLShortener()

        with self.assertRaises(ValueError):
            shortener.shorten("ftp://example.com/file")

        self.assertEqual(shortener.shorten("https://example.com/valid"), "0")


if __name__ == "__main__":
    unittest.main()
