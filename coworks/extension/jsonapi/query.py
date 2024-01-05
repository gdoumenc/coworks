import typing as t

from .data import JsonApiDataMixin


@t.runtime_checkable
class Pagination(t.Protocol, t.Iterable):
    total: int
    page: int
    pages: int
    per_page: int
    has_prev: bool
    prev_num: int
    has_next: bool
    next_num: int


@t.runtime_checkable
class Query(t.Protocol):
    def paginate(self, *, page, per_page, max_per_page) -> Pagination:
        ...

    def all(self) -> list[JsonApiDataMixin]:
        ...
