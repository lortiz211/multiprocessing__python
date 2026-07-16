import bisect
from collections.abc import Iterable, Iterator, Mapping
from typing import Any, Protocol, cast, overload


class Comparable(Protocol):
    """Protocol for types that support ordering comparisons.

    Mirrors typeshed's ``SupportsRichComparison``: ``__eq__``/``__ne__`` are
    inherited from ``object``, and the ordering dunders take a positional-only
    argument so builtins like ``str``/``int`` structurally satisfy the protocol.
    """

    def __lt__(self, other: Any, /) -> bool: ...

    def __le__(self, other: Any, /) -> bool: ...

    def __gt__(self, other: Any, /) -> bool: ...

    def __ge__(self, other: Any, /) -> bool: ...


class Lookup(Mapping[Comparable, Any]):
    @overload
    def __init__(self, source: Iterable[tuple[Comparable, Any]]) -> None: ...

    @overload
    def __init__(self, source: "Mapping[Comparable, Any]") -> None: ...

    def __init__(self, source: Any):
        sorted_pairs: list[tuple[Comparable, Any]]
        match source:
            case Iterable() as an_iter:
                # Assume it is pairs
                sorted_pairs = sorted(cast(Iterable[tuple[Comparable, Any]], an_iter))
            case Mapping() as a_map:
                sorted_pairs = sorted(
                    cast(Iterable[tuple[Comparable, Any]], a_map.items())
                )
            case _:
                sorted_pairs = []
        self.key_list: list[Comparable] = [p[0] for p in sorted_pairs]
        self.value_list: list[Any] = [p[1] for p in sorted_pairs]

    def __len__(self) -> int:
        return len(self.key_list)

    def __iter__(self) -> Iterator[Comparable]:
        return iter(self.key_list)

    def __contains__(self, key: object) -> bool:
        index = bisect.bisect_left(self.key_list, cast(Comparable, key))
        return key == self.key_list[index]

    def __getitem__(self, key: Comparable) -> Any:
        index = bisect.bisect_left(self.key_list, key)
        if key == self.key_list[index]:
            return self.value_list[index]
        raise KeyError(key)


def main() -> None:
    x = Lookup([("z", "Zillah")])
    print(x["z"])
