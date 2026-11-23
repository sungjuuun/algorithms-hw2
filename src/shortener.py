import unicodedata
from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class URLShortener:
    def __init__(self):
        self._url_to_code = HashTable()
        self._code_to_url = HashTable()
        self._next_id = 0

    def shorten(self, url: str) -> str:
        self._validate_url(url)

        if url in self._url_to_code:
            return self._url_to_code.get(url)

        code = encode(self._next_id)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str:
        if not isinstance(code, str):
            raise TypeError("code must be a string")

        identifier = decode(code)
        if encode(identifier) != code:
            raise ValueError("code must be in canonical Base62 form")
        return self._code_to_url.get(code)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str):
            raise TypeError("url must be a string")
        if not url:
            raise ValueError("url must not be empty")
        if len(url) > 2048:
            raise ValueError("url must not exceed 2048 characters")
        if any(character.isspace() or unicodedata.category(character) == "Cc" for character in url):
            raise ValueError("url must not contain whitespace or control characters")

        try:
            parts = urlsplit(url)
            host = parts.hostname
            port = parts.port
        except ValueError as exc:
            raise ValueError("url is malformed") from exc

        if parts.scheme.lower() not in ("http", "https") or not host:
            raise ValueError("url must be an absolute HTTP(S) URL with a host")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("url port must be between 1 and 65535")
