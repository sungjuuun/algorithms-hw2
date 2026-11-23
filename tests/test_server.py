import http.client
import threading
import unittest
from urllib.parse import urlencode

from src.server import create_server


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

    def test_table_shows_actual_bucket_hash_and_escaped_key(self):
        url = "https://example.com/<script>alert(1)</script>"
        self.server.shortener.shorten(url)
        bucket = self.server.shortener._url_to_code.bucket_index(url)

        status, _, body = self.request("GET", "/table")

        self.assertEqual(status, 200)
        self.assertIn("Horner result (mod 4093)", body)
        self.assertIn(f"<td>{bucket}</td><td>{bucket}</td>", body)
        self.assertIn("&lt;script&gt;", body)
        self.assertNotIn("<script>", body)

    def test_undefined_path_and_unsupported_method(self):
        status, _, _ = self.request("GET", "/missing")
        self.assertEqual(status, 404)

        status, _, _ = self.request("BREW", "/")
        self.assertEqual(status, 405)

        status, _, _ = self.request("POST", "/")
        self.assertEqual(status, 405)


if __name__ == "__main__":
    unittest.main()
