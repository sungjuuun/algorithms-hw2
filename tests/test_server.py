import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import ShortenerRequestHandler, create_server
from src.shortener import URLShortener


class Headers:
    def __init__(self, pairs=()):
        self._pairs = tuple(pairs)

    def __iter__(self):
        return (name for name, _ in self._pairs)

    def items(self):
        return self._pairs


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.connection = http.client.HTTPConnection(
            "127.0.0.1", self.server.server_port
        )

    def tearDown(self):
        self.connection.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, headers=None):
        request_headers = Headers(()) if headers is None else Headers(headers)
        self.connection.request(
            method, path, body=body, headers=request_headers
        )
        response = self.connection.getresponse()
        response_body = response.read().decode("utf-8")
        return response.status, response.getheader("Location"), response_body

    def post_form(self, fields):
        body = urlencode(fields)
        return self.request(
            "POST",
            "/shorten",
            body,
            (("Content-Type", "application/x-www-form-urlencoded"),),
        )

    def test_home_page_returns_form(self):
        status, _, body = self.request("GET", "/")

        self.assertEqual(status, 200)
        self.assertIn('name="url"', body)
        self.assertIn('action="/shorten"', body)

    def test_successful_post_returns_short_code_and_link(self):
        status, _, body = self.post_form(
            (("url", "https://example.com/path"),)
        )

        self.assertEqual(status, 200)
        self.assertIn('href="/0"', body)
        self.assertIn("/0", body)

    def test_missing_duplicate_and_blank_url_fields_return_400(self):
        cases = (
            (),
            (("url", "https://example.com/one"), ("url", "https://example.com/two")),
            (("url", ""), ("url", "https://example.com/one")),
        )
        for fields in cases:
            with self.subTest(fields=fields):
                status, _, _ = self.post_form(fields)
                self.assertEqual(status, 400)

    def test_invalid_url_returns_400(self):
        status, _, _ = self.post_form((("url", "ftp://example.com/"),))

        self.assertEqual(status, 400)

    def test_redirect_unknown_and_invalid_codes(self):
        self.server.shortener.shorten("https://example.com/known")

        status, location, _ = self.request("GET", "/0")
        self.assertEqual(status, 302)
        self.assertEqual(location, "https://example.com/known")

        status, _, _ = self.request("GET", "/1")
        self.assertEqual(status, 404)

        for path in ("/!", "/00"):
            with self.subTest(path=path):
                status, _, _ = self.request("GET", path)
                self.assertEqual(status, 400)

    def test_shortening_and_redirect_work_with_both_strategies(self):
        for strategy in ("chaining", "linear_probing"):
            with self.subTest(strategy=strategy):
                self.server.shortener = URLShortener(strategy=strategy)
                url = f"https://example.com/{strategy}"

                status, _, body = self.post_form((("url", url),))

                self.assertEqual(status, 200)
                self.assertIn('href="/0"', body)
                status, location, _ = self.request("GET", "/0")
                self.assertEqual(status, 302)
                self.assertEqual(location, url)

    def test_table_shows_actual_bucket_hash_and_escaped_key(self):
        url = "https://example.com/<script>alert(1)</script>"
        for strategy in ("chaining", "linear_probing"):
            with self.subTest(strategy=strategy):
                self.server.shortener = URLShortener(strategy=strategy)
                self.server.shortener.shorten(url)
                table = self.server.shortener._url_to_code
                initial_index = table.bucket_index(url)

                status, _, body = self.request("GET", "/table")

                self.assertEqual(status, 200)
                self.assertIn("Horner hash", body)
                self.assertIn(f"{initial_index}", body)
                self.assertIn("&lt;script&gt;", body)
                self.assertNotIn("<script>", body)
                self.assertIn("<details>", body)
                self.assertIn("Horner hash calculation", body)
                self.assertIn("Final bucket:", body)
                if strategy == "chaining":
                    self.assertIn("Separate chaining", body)
                    self.assertIn("Linked nodes", body)
                    self.assertIn("NULL", body)
                else:
                    self.assertIn("Linear probing", body)
                    self.assertIn("Stored slot", body)
                    self.assertIn("Probe order", body)
                    self.assertIn("Short link", body)

    def test_horner_details_show_each_ordinal_and_intermediate_hash(self):
        details = ShortenerRequestHandler._horner_explanation("ab", 1000, 105)

        self.assertIn("<details>", details)
        self.assertIn("ord = 97", details)
        self.assertIn("(31 * 0 + 97) mod 1000 = 97", details)
        self.assertIn("ord = 98", details)
        self.assertIn("(31 * 97 + 98) mod 1000 = 105", details)
        self.assertIn("Final bucket: 105", details)

    def test_chaining_visualizes_colliding_nodes_and_short_links(self):
        shortener = URLShortener(strategy="chaining", table_size=3)
        matching_urls = []
        for index in range(100):
            url = f"https://example.com/{index}"
            if shortener._url_to_code.bucket_index(url) == 2:
                matching_urls.append(url)
                if len(matching_urls) == 2:
                    break
        self.assertEqual(len(matching_urls), 2)
        shortener.shorten(matching_urls[0])
        shortener.shorten(matching_urls[1])
        self.server.shortener = shortener

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn(" &rarr; ", body)
        self.assertIn(" &rarr; NULL", body)
        self.assertIn(matching_urls[0], body)
        self.assertIn(matching_urls[1], body)
        self.assertIn('href="/0">/0</a>', body)
        self.assertIn('href="/1">/1</a>', body)

    def test_linear_table_shows_wrapped_probe_path_and_final_slot(self):
        shortener = URLShortener(strategy="linear_probing", table_size=3)
        matching_urls = []
        for index in range(100):
            url = f"https://example.com/{index}"
            if shortener._url_to_code.bucket_index(url) == 2:
                matching_urls.append(url)
                if len(matching_urls) == 2:
                    break
        self.assertEqual(len(matching_urls), 2)
        shortener.shorten(matching_urls[0])
        shortener.shorten(matching_urls[1])
        self.server.shortener = shortener

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("<td>2 &rarr; 0</td><td>0</td>", body)
        self.assertIn("mod 3", body)

    def test_undefined_path_and_unsupported_method(self):
        status, _, _ = self.request("GET", "/missing")
        self.assertEqual(status, 404)

        status, _, _ = self.request("BREW", "/")
        self.assertEqual(status, 405)

        status, _, _ = self.request("POST", "/")
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
