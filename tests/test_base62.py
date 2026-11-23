import unittest

from src.base62 import decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero_and_digit_boundaries(self):
        self.assertEqual(encode(0), "0")
        self.assertEqual(encode(9), "9")
        self.assertEqual(encode(10), "a")
        self.assertEqual(encode(35), "z")
        self.assertEqual(encode(36), "A")
        self.assertEqual(encode(61), "Z")
        self.assertEqual(encode(62), "10")

    def test_decode_digit_boundaries(self):
        self.assertEqual(decode("0"), 0)
        self.assertEqual(decode("9"), 9)
        self.assertEqual(decode("a"), 10)
        self.assertEqual(decode("z"), 35)
        self.assertEqual(decode("A"), 36)
        self.assertEqual(decode("Z"), 61)
        self.assertEqual(decode("10"), 62)

    def test_round_trip_large_integer(self):
        number = 2**128 - 1
        self.assertEqual(decode(encode(number)), number)

    def test_decode_accepts_leading_zeroes(self):
        self.assertEqual(decode("0001"), 1)

    def test_encode_rejects_non_integer_values(self):
        for value in (True, 1.5, "12", None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    encode(value)

    def test_encode_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_decode_rejects_non_string_values(self):
        for value in (62, None):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    decode(value)

    def test_decode_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            decode("")

    def test_decode_rejects_characters_outside_alphabet(self):
        for value in ("!", "é", "１"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    decode(value)


if __name__ == "__main__":
    unittest.main()
