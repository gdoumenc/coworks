import contextlib
import typing as t
from collections import defaultdict
from datetime import datetime

from jsonapi_pydantic.v1_0 import Link
from jsonapi_pydantic.v1_0 import TopLevel
from pydantic.networks import HttpUrl
from sqlalchemy import Column
from sqlalchemy import ColumnOperators
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql import and_
from werkzeug.exceptions import UnprocessableEntity
from werkzeug.local import LocalProxy

from coworks import request
from coworks.utils import nr_url
from coworks.utils import str_to_bool
from .data import JsonApiDataMixin
from .query import Pagination


class FetchingContext:

    def __init__(self, include: str | None = None, fields__: dict[str, str] | None = None,
                 filters__: dict[str, str] | None = None, sort: str | None = None,
                 page__number__: int | None = None, page__size__: int | None = None, page__max__: int | None = None):
        self.include = list(map(str.strip, include.split(','))) if include else []
        self._fields = fields__ if fields__ is not None else {}
        filters__ = filters__ if filters__ is not None else {}
        self._sort = list(map(str.strip, sort.split(','))) if sort else []
        self.page = page__number__
        self.per_page = page__size__ or 100
        self.max_per_page = page__max__ or 100

        self._filters: dict = defaultdict(list)
        for k, v in filters__.items():
            try:
                json_type, filter = k.rsplit('.', 1)
                self._filters[json_type].append((filter, v))
            except ValueError:
                msg = f"The filter parameter '{k}' must be of the form 'filter[type.value][oper]'"
                raise ValueError(msg)

        self.connection_manager = contextlib.nullcontext()

    def field_names(self, jsonapi_type) -> list[str]:
        if jsonapi_type in self._fields:
            fields = self._fields[jsonapi_type]
            if isinstance(fields, list):
                if len(fields) != 1:
                    msg = f"Wrong field value '{fields}': multiple fields parameter must be a comma-separated"
                    raise UnprocessableEntity(msg)
                field = fields[0]
            else:
                field = fields
            return list(map(str.strip, field.split(',')))
        return []

    def sql_filters(self, *sql_model: JsonApiDataMixin):
        """Returns the list of filters as a SQLAlchemy filter.
        If several sql_model are given, add .join() in the query

        :param sql_model: the SQLAlchemy model (used to get the SQLAlchemy filter)
        """
        _sql_filters: list[ColumnOperators] = []
        for model in sql_model:
            jsonapi_type = model.jsonapi_type.__get__(model)  # type:ignore[attr-defined]
            filter_parameters = self._filters.get(jsonapi_type, {})

            for key, value in filter_parameters:

                # If parameters are defined in body payload they may be not defined as list
                if not isinstance(value, list):
                    value = [value]
                oper = None

                # filter operator
                # idea from https://discuss.jsonapi.org/t/share-propose-a-filtering-strategy/257
                if "____" in key:
                    key, oper = key.split('____', 1)

                # if the key is named (for allowing composition of filters)
                if ':' in key:
                    name, key = key.split(':', 1)

                # if the key is a boolean operator then the value is an expression

                column = getattr(model, key, None)
                if column is None:
                    msg = f"Wrong '{key}' property for sql model '{jsonapi_type}' in filters parameters"
                    raise UnprocessableEntity(msg)

                if isinstance(column.property, ColumnProperty):
                    _type = getattr(column, 'type', None)
                    if _type:
                        if _type.python_type is bool:
                            _sql_filters.append(*bool_sql_filter(jsonapi_type, key, column, oper, value))
                        elif _type.python_type is str:
                            _sql_filters.append(*str_sql_filter(jsonapi_type, key, column, oper, value))
                        elif _type.python_type is int:
                            _sql_filters.append(*int_sql_filter(jsonapi_type, key, column, oper, value))
                        elif _type.python_type is datetime:
                            _sql_filters.append(*datetime_sql_filter(jsonapi_type, key, column, oper, value))
                    else:
                        _sql_filters.append(column.in_(value))
                elif isinstance(column.property, RelationshipProperty):
                    if not isinstance(value, dict):
                        msg = (f"Wrong '{value}' value for sql model '{jsonapi_type}'"
                               " in filters parameters (should be a dict).")
                        raise UnprocessableEntity(msg)
                    for k, v in value.items():
                        condition = column.has(**{k: v[0]})
                        if len(v) > 1:
                            for or_v in v[1:]:
                                condition = and_(condition, column.has(**{k: or_v}))
                        _sql_filters.append(condition)

        return _sql_filters

    def sql_order_by(self, sql_model):
        """Returns a SQLAlchemy order from model using fetching order keys.

        :param sql_model: the SQLAlchemy model (used to get the SQLAlchemy order)."""
        _sql_order_by = []
        for key in self._sort:
            if key.startswith('-'):
                column = getattr(sql_model, key[1:]).desc()
            else:
                column = getattr(sql_model, key)
            _sql_order_by.append(column)
        return _sql_order_by

    def _add_branch(self, tree, vector, value):
        key = vector[0]

        if len(vector) == 1:
            tree[key] = value
        else:
            sub_tree = tree.get(key, {})
            tree[key] = self._add_branch(sub_tree, vector[1:], value)

        return tree

    @staticmethod
    def add_pagination(toplevel: TopLevel, pagination: Pagination):
        if pagination.total > 1:
            links = toplevel.links or {}
            if pagination.has_prev:
                links["prev"] = Link(
                    href=HttpUrl(nr_url(request.path, {"page[number]": pagination.prev_num}, merge_query=True))
                )
            if pagination.has_next:
                links["next"] = Link(
                    href=HttpUrl(nr_url(request.path, {"page[number]": pagination.next_num}, merge_query=True))
                )
            toplevel.links = links

        meta = toplevel.meta or {}
        meta["count"] = pagination.total
        meta["pagination"] = {
            "page": pagination.page,
            "pages": pagination.pages,
            "per_page": pagination.per_page,
        }
        toplevel.meta = meta


def create_fetching_context_proxy(include: str | None = None, fields__: dict | None = None,
                                  filters__: dict | None = None, sort: str | None = None,
                                  page__number__: int | None = None, page__size__: int | None = None,
                                  page__max__: int | None = None):
    context = FetchingContext(include, fields__, filters__, sort, page__number__, page__size__, page__max__)
    setattr(request, 'fetching_context', context)


fetching_context = t.cast(FetchingContext,
                          LocalProxy(lambda: getattr(request, 'fetching_context', 'Not in JsonApi context')))


def bool_sql_filter(jsonapi_type, key, column, oper, value) -> list[ColumnOperators]:
    """Boolean filter."""
    if len(value) != 1:
        msg = f"Multiple boolean values '{key}' property on model '{jsonapi_type}' is not allowed"
        raise UnprocessableEntity(msg)
    return [column == str_to_bool(value[0])]


def str_sql_filter(jsonapi_type, key, column, oper, value) -> list[ColumnOperators]:
    """String filter."""
    oper = oper or 'eq'
    if oper not in ('eq', 'ilike', 'contains'):
        msg = f"Undefined operator '{oper}' for string value"
        raise UnprocessableEntity(msg)
    if oper == 'eq':
        return [column.in_(value)]
    if oper == 'ilike':
        return [column.ilike(str(v)) for v in value]
    if oper == 'contains':
        return [column.contains(str(v)) for v in value]


def int_sql_filter(jsonapi_type, key, column, oper, value) -> list[ColumnOperators]:
    """Datetime filter."""
    oper = oper or 'eq'
    if oper not in ('eq', 'ge', 'gt', 'le', 'lt'):
        msg = f"Undefined operator '{oper}' for integer value"
        raise UnprocessableEntity(msg)
    return [sort_operator(column, oper, int(v)) for v in value]


def datetime_sql_filter(jsonapi_type, key, column, oper, value) -> list[ColumnOperators]:
    """Datetime filter."""
    oper = oper or 'eq'
    if oper not in ('eq', 'ge', 'gt', 'le', 'lt'):
        msg = f"Undefined operator '{oper}' for datetime value"
        raise UnprocessableEntity(msg)
    return [sort_operator(column, oper, datetime.fromisoformat(v)) for v in value]


def sort_operator(column: Column, oper, value) -> ColumnOperators:
    if oper == 'eq':
        return column == value
    if oper == 'ge':
        return column >= value
    if oper == 'gt':
        return column > value
    if oper == 'le':
        return column <= value
    if oper == 'lt':
        return column < value
