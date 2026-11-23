class _Entry:
    __slots__ = ("key", "value")

    def __init__(self, key: str, value: object):
        self.key = key
        self.value = value


class LinearProbingHashTable:
    def __init__(self, M: int = 4093, max_load: float | None = None):
        if isinstance(M, bool) or not isinstance(M, int):
            raise TypeError("M must be an integer")
        if M <= 0:
            raise ValueError("M must be positive")

        self._slots: list[_Entry | None] = [None] * M
        self._size = 0
        self._max_load = max_load

    def bucket_index(self, key: str) -> int:
        self._validate_key(key)

        index = 0
        for character in key:
            index = (31 * index + ord(character)) % len(self._slots)
        return index

    def put(self, key: str, value: object) -> None:
        initial_index = self.bucket_index(key)

        for offset in range(len(self._slots)):
            index = (initial_index + offset) % len(self._slots)
            entry = self._slots[index]
            if entry is None:
                self._slots[index] = _Entry(key, value)
                self._size += 1
                return
            if entry.key == key:
                entry.value = value
                return

        raise OverflowError("hash table is full")

    def get(self, key: str) -> object:
        index, _ = self._find(key)
        if index is None:
            raise KeyError(key)
        entry = self._slots[index]
        if entry is None:
            raise KeyError(key)
        return entry.value

    def probe_count(self, key: str) -> int:
        _, count = self._find(key)
        return count

    def probe_path(self, key: str) -> tuple[int, ...]:
        initial_index = self.bucket_index(key)
        path = []
        for offset in range(len(self._slots)):
            index = (initial_index + offset) % len(self._slots)
            path.append(index)
            entry = self._slots[index]
            if entry is None or entry.key == key:
                break
        return tuple(path)

    def items(self):
        for entry in self._slots:
            if entry is not None:
                yield entry.key, entry.value

    @property
    def load_factor(self) -> float:
        return self._size / len(self._slots)

    @property
    def capacity(self) -> int:
        return len(self._slots)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: object) -> bool:
        self._validate_key(key)
        index, _ = self._find(key)
        return index is not None

    def _find(self, key: str) -> tuple[int | None, int]:
        initial_index = self.bucket_index(key)
        for offset in range(len(self._slots)):
            index = (initial_index + offset) % len(self._slots)
            entry = self._slots[index]
            if entry is None:
                return None, offset + 1
            if entry.key == key:
                return index, offset + 1
        return None, len(self._slots)

    @staticmethod
    def _validate_key(key: object) -> None:
        if not isinstance(key, str):
            raise TypeError("key must be a string")
