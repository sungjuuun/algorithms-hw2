#!/usr/bin/env python3
"""HTTP interface for the in-memory URL shortener."""

from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

from src.shortener import URLShortener


MAX_FORM_BYTES = 65536


class ShortenerHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        shortener: URLShortener | None = None,
    ) -> None:
        self.shortener = shortener if shortener is not None else URLShortener()
        super().__init__(server_address, ShortenerRequestHandler)


class ShortenerRequestHandler(BaseHTTPRequestHandler):
    server: ShortenerHTTPServer

    def do_GET(self) -> None:
        path = self._request_path()
        if path is None:
            return
        if path == "/":
            self._send_html(
                HTTPStatus.OK,
                '<!doctype html><html><body><h1>URL shortener</h1>'
                '<form action="/shorten" method="post">'
                '<label>URL <input type="url" name="url" required></label>'
                '<button type="submit">Shorten</button></form></body></html>',
            )
        elif path == "/shorten":
            self._send_method_not_allowed()
        elif path == "/table":
            self._send_html(HTTPStatus.OK, self._table_html())
        elif path.startswith("/") and path.count("/") == 1:
            self._redirect(path[1:])
        else:
            self._send_not_found()

    def do_POST(self) -> None:
        path = self._request_path()
        if path is None:
            return
        if path != "/shorten":
            if self._is_known_path(path):
                self._send_method_not_allowed()
            else:
                self._send_not_found()
            return

        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != (
            "application/x-www-form-urlencoded"
        ):
            self._send_bad_request()
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._send_bad_request()
            return
        if not 0 <= content_length <= MAX_FORM_BYTES:
            self._send_bad_request()
            return

        body = self.rfile.read(content_length)
        if len(body) != content_length:
            self._send_bad_request()
            return
        try:
            form_data = body.decode("utf-8")
            fields = parse_qsl(form_data, keep_blank_values=True)
        except (UnicodeDecodeError, ValueError):
            self._send_bad_request()
            return

        urls = [value for name, value in fields if name == "url"]
        if len(urls) != 1:
            self._send_bad_request()
            return

        url = urls[0]
        try:
            code = self.server.shortener.shorten(url)
        except ValueError:
            self._send_bad_request()
            return

        escaped_code = html.escape(code, quote=True)
        escaped_url = html.escape(url, quote=True)
        self._send_html(
            HTTPStatus.OK,
            "<!doctype html><html><body><h1>Short URL created</h1>"
            f'<p><a href="/{escaped_code}">/{escaped_code}</a></p>'
            f"<p>Original URL: {escaped_url}</p></body></html>",
        )

    def send_error(
        self,
        code: int,
        message: str | None = None,
        explain: str | None = None,
    ) -> None:
        if code == HTTPStatus.NOT_IMPLEMENTED:
            self._send_method_not_allowed()
            return
        super().send_error(code, message, explain)

    def _request_path(self) -> str | None:
        try:
            return urlsplit(self.path).path
        except ValueError:
            self._send_bad_request()
            return None

    @staticmethod
    def _is_known_path(path: str) -> bool:
        return path in ("/", "/shorten", "/table") or (
            path.startswith("/") and path.count("/") == 1 and len(path) > 1
        )

    def _redirect(self, code: str) -> None:
        try:
            url = self.server.shortener.expand(code)
        except ValueError:
            self._send_bad_request()
            return
        except KeyError:
            self._send_not_found()
            return

        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _table_html(self) -> str:
        table = self.server.shortener._url_to_code
        bucket_count = len(table._buckets)
        rows = []
        for bucket_number, node in enumerate(table._buckets):
            while node is not None:
                horner_result = table.bucket_index(node.key)
                rows.append(
                    "<tr>"
                    f"<td>{bucket_number}</td>"
                    f"<td>{horner_result}</td>"
                    f"<td>{html.escape(node.key, quote=True)}</td>"
                    f"<td>{html.escape(str(node.value), quote=True)}</td>"
                    "</tr>"
                )
                node = node.next

        if rows:
            table_body = "".join(rows)
        else:
            table_body = '<tr><td colspan="4">No URLs stored</td></tr>'

        return (
            "<!doctype html><html><body><h1>Hash table</h1>"
            f"<p>Separate chaining table, M={bucket_count}</p>"
            "<table><thead><tr><th>Bucket index</th>"
            f"<th>Horner result (mod {bucket_count})</th>"
            "<th>URL key</th><th>Code</th>"
            f"</tr></thead><tbody>{table_body}</tbody></table>"
            "</body></html>"
        )

    def _send_html(self, status: HTTPStatus, body: str) -> None:
        encoded_body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded_body)))
        self.end_headers()
        self.wfile.write(encoded_body)

    def _send_bad_request(self) -> None:
        self._send_html(
            HTTPStatus.BAD_REQUEST,
            "<!doctype html><html><body><h1>Bad Request</h1></body></html>",
        )

    def _send_not_found(self) -> None:
        self._send_html(
            HTTPStatus.NOT_FOUND,
            "<!doctype html><html><body><h1>Not Found</h1></body></html>",
        )

    def _send_method_not_allowed(self) -> None:
        body = (
            "<!doctype html><html><body>"
            "<h1>Method Not Allowed</h1></body></html>"
        ).encode("utf-8")
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, POST")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    shortener: URLShortener | None = None,
) -> ShortenerHTTPServer:
    return ShortenerHTTPServer((host, port), shortener)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    print(f"Serving on http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
