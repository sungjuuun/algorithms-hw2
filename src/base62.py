"""Base62 encoding and decoding."""

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
_BASE = len(_ALPHABET)


def encode(n: int) -> str:
    """Encode a non-negative integer as a Base62 string."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return "0"

    digits = []
    while n:
        n, remainder = divmod(n, _BASE)
        digits.append(_ALPHABET[remainder])
    return "".join(reversed(digits))


def decode(s: str) -> int:
    """Decode a Base62 string to a non-negative integer."""
    if not isinstance(s, str):
        raise TypeError("s must be a string")
    if not s:
        raise ValueError("s must not be empty")

    value = 0
    for char in s:
        digit = _ALPHABET.find(char)
        if digit == -1:
            raise ValueError(f"invalid Base62 character: {char!r}")
        value = value * _BASE + digit
    return value
