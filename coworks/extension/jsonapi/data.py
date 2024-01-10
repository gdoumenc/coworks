import typing as t
from math import ceil

from pydantic import BaseModel
from pydantic import field_validator

if t.TYPE_CHECKING:
    from fetching import FetchingContext


class CursorPagination(BaseModel):
    """Pagination based on a cursor model (total and per_page must be defined)"""
    total: int
    page: int | None
    per_page: int | None

    @field_validator("page")
    def set_page(cls, page):
        return page or 1

    @field_validator("per_page")
    def set_per_page(cls, per_page):
        return per_page or 20

    @property
    def pages(self) -> int:
        if not self.total:
            return 1
        assert self.per_page is not None  # by the validator
        return ceil(self.total / self.per_page)

    @property
    def has_prev(self) -> bool:
        assert self.page is not None  # by the validator
        return self.page > 1

    @property
    def prev_num(self) -> int | None:
        if not self.has_prev:
            return None
        assert self.page is not None  # by the validator
        return self.page - 1

    @property
    def has_next(self) -> bool:
        assert self.page is not None  # by the validator
        return self.page < self.pages

    @property
    def next_num(self) -> int | None:
        if not self.has_next:
            return None
        assert self.page is not None  # by the validator
        return self.page + 1


class JsonApiDataMixin:
    """Any data structure which may be transformed to JSON:API resource.
    """

    @property
    def jsonapi_type(self) -> str:
        return 'unknown'

    @property
    def jsonapi_id(self) -> str:
        return 'unknown'

    @property
    def jsonapi_self_link(self):
        return "https://monsite.com/missing_entry"

    def jsonapi_model_dump(self, context: 'FetchingContext') -> dict[str, t.Any]:
        return {}


class JsonApiDict(dict, JsonApiDataMixin):
    """Dict data for JSON:API resource"""

    @property
    def jsonapi_type(self) -> str:
        return self['type']

    @property
    def jsonapi_id(self) -> str:
        return str(self['id'])

    def jsonapi_model_dump(self, context: "FetchingContext", exclude: list[str] | None = None) -> dict[str, t.Any]:
        exclude = exclude or []
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in self.items() if
                (not fields or k in fields) and k not in exclude}  # type:ignore


class JsonApiHashableMixin(JsonApiDataMixin):
    """Hashable JsonApiDataMixin"""

    def __hash__(self) -> int:
        return hash(self.jsonapi_type + str(self.jsonapi_id))


class JsonApiDataSet(dict[JsonApiDataMixin, dict]):
    """Set of resources for included part of TopLevel."""

    def extract(self, *, type, id) -> dict | None:
        for resource in self:
            if resource.jsonapi_type == type and resource.jsonapi_id == id:
                return self[resource]
        return None
