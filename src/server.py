#!/usr/bin/env python3
"""HTTP interface for the in-memory URL shortener."""

from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qsl, urlsplit

from src.linear_probing_hash_table import LinearProbingHashTable
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
        bucket_count = table.capacity
        rows = []
        if isinstance(table, LinearProbingHashTable):
            for key, value in table.items():
                initial_index = table.bucket_index(key)
                probe_path = table.probe_path(key)
                displayed_path = " &rarr; ".join(str(slot) for slot in probe_path)
                escaped_code = html.escape(str(value), quote=True)
                short_link = (
                    f'<a href="/{escaped_code}">/{escaped_code}</a>'
                )
                rows.append(
                    "<tr>"
                    f"<td>{initial_index}</td>"
                    f"<td>{self._horner_explanation(key, bucket_count, initial_index)}</td>"
                    f"<td>{displayed_path}</td>"
                    f"<td>{probe_path[-1]}</td>"
                    f"<td>{html.escape(key, quote=True)}</td>"
                    f"<td>{escaped_code}</td>"
                    f"<td>{short_link}</td>"
                    "</tr>"
                )
            table_heading = f"Linear probing table, M={bucket_count}"
            table_headers = (
                "<th>Initial hash</th><th>Horner hash calculation</th>"
                "<th>Probe order (checked slots)</th><th>Stored slot</th>"
                "<th>URL key</th><th>Code</th><th>Short link</th>"
            )
            empty_row = '<tr><td colspan="7">No URLs stored</td></tr>'
        else:
            for bucket_number, node in enumerate(table._buckets):
                chain_nodes = []
                while node is not None:
                    escaped_code = html.escape(str(node.value), quote=True)
                    short_link = (
                        f'<a href="/{escaped_code}">/{escaped_code}</a>'
                    )
                    chain_nodes.append(
                        '<span class="chain-node">'
                        f"<strong>URL key:</strong> "
                        f"{html.escape(node.key, quote=True)}; "
                        f"<strong>Code:</strong> {escaped_code}; "
                        f"<strong>Short link:</strong> {short_link}; "
                        f"{self._horner_explanation(node.key, bucket_count, bucket_number)}"
                        "</span>"
                    )
                    node = node.next
                if chain_nodes:
                    chain = " &rarr; ".join((*chain_nodes, "NULL"))
                    rows.append(
                        f"<tr><td>{bucket_number}</td>"
                        f'<td><div class="chain">{chain}</div></td></tr>'
                    )
            table_heading = f"Separate chaining table, M={bucket_count}"
            table_headers = (
                "<th>Bucket index</th><th>Linked nodes</th>"
            )
            empty_row = '<tr><td colspan="2">No URLs stored</td></tr>'

        if rows:
            table_body = "".join(rows)
        else:
            table_body = empty_row

        return (
            "<!doctype html><html><body><h1>Hash table</h1>"
            f"<p>{table_heading}</p>"
            f"<table><thead><tr>{table_headers}"
            f"</tr></thead><tbody>{table_body}</tbody></table>"
            "</body></html>"
        )

    @staticmethod
    def _horner_explanation(key: str, modulus: int, result: int) -> str:
        value = 0
        steps = ["<li>h<sub>0</sub> = 0</li>"]
        for position, character in enumerate(key, start=1):
            previous_value = value
            next_value = (31 * value + ord(character)) % modulus
            steps.append(
                f"<li>{html.escape(repr(character), quote=True)}: "
                f"ord = {ord(character)}; "
                f"h<sub>{position}</sub> = "
                f"(31 * {previous_value} + {ord(character)}) "
                f"mod {modulus} = {next_value}</li>"
            )
            value = next_value
        if value != result:
            raise RuntimeError("Horner explanation does not match the table bucket")
        return (
            f"<details><summary>Horner hash calculation for bucket {result}"
            f"</summary><ol>{''.join(steps)}</ol>"
            f"<p>Final bucket: {value}</p></details>"
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
    parser.add_argument(
        "--strategy",
        choices=("chaining", "linear_probing"),
        default="chaining",
    )
    args = parser.parse_args()

    server = create_server(
        args.host,
        args.port,
        URLShortener(strategy=args.strategy),
    )
    print(f"Serving on http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
