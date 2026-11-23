class _Node:
    __slots__ = ("key", "value", "next")

    def __init__(self, key: str, value: object, next_node: "_Node | None" = None):
        self.key = key
        self.value = value
        self.next = next_node


class HashTable:
    def __init__(self, M: int = 4093, max_load: float | None = None):
        if isinstance(M, bool) or not isinstance(M, int):
            raise TypeError("M must be an integer")
        if M <= 0:
            raise ValueError("M must be positive")

        self._buckets: list[_Node | None] = [None] * M
        self._size = 0
        self._max_load = max_load

    def bucket_index(self, key: str) -> int:
        self._validate_key(key)

        index = 0
        for character in key:
            index = (31 * index + ord(character)) % len(self._buckets)
        return index

    def put(self, key: str, value: object) -> None:
        index = self.bucket_index(key)
        node = self._buckets[index]

        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1

    def get(self, key: str) -> object:
        index = self.bucket_index(key)
        node = self._buckets[index]

        while node is not None:
            if node.key == key:
                return node.value
            node = node.next

        raise KeyError(key)

    def items(self):
        for node in self._buckets:
            while node is not None:
                yield node.key, node.value
                node = node.next

    def probe_count(self, key: str) -> int:
        index = self.bucket_index(key)
        count = 0
        node = self._buckets[index]

        while node is not None:
            count += 1
            if node.key == key:
                break
            node = node.next
        return count

    @property
    def load_factor(self) -> float:
        return self._size / len(self._buckets)

    @property
    def capacity(self) -> int:
        return len(self._buckets)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        self._validate_key(key)
        index = self.bucket_index(key)
        node = self._buckets[index]

        while node is not None:
            if node.key == key:
                return True
            node = node.next
        return False

    @staticmethod
    def _validate_key(key: object) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
