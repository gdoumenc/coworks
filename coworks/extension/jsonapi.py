import asyncio
import contextlib
import typing as t
from functools import update_wrapper
from inspect import signature

from coworks import TechMicroService
from coworks import request
from coworks.utils import nr_url
from coworks.utils import str_to_bool
from flask import current_app
from flask import make_response
from jsonapi_pydantic.v1_0 import Error
from jsonapi_pydantic.v1_0 import ErrorLinks
from jsonapi_pydantic.v1_0 import Link
from jsonapi_pydantic.v1_0 import Relationship
from jsonapi_pydantic.v1_0 import RelationshipLinks
from jsonapi_pydantic.v1_0 import Resource
from jsonapi_pydantic.v1_0 import ResourceIdentifier
from jsonapi_pydantic.v1_0 import TopLevel
from pydantic import ValidationError
from pydantic.networks import HttpUrl
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.sql import or_
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import NotFound
from werkzeug.exceptions import UnprocessableEntity
from werkzeug.local import LocalProxy

fetching_context = t.cast("FetchingContext",
                          LocalProxy(lambda: getattr(request, 'fetching_context', 'Not in JsonApi context')))


class JsonApiBaseModelMixin:
    """Any pydantic base model which may be transformed to JSON:API resource.
    """

    def __hash__(self):
        return hash(self.jsonapi_type + str(self.jsonapi_id))

    @property
    def jsonapi_type(self) -> str:
        return self.__class__.__name__.lower()

    @property
    def jsonapi_id(self) -> str:
        return '0'

    @property
    def jsonapi_self_link(self):
        return "https://monsite.com/missing_entry"

    def jsonapi_model_dump(self, context: "FetchingContext") -> dict[str, t.Any]:
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in self.model_dump().items() if fields is None or k in fields}  # type:ignore


class Pagination(t.Protocol, t.Iterable):
    total: int
    has_prev: bool
    prev_num: int
    has_next: bool
    next_num: int


class Query(t.Protocol):
    def paginate(self, *, page, per_page, max_per_page) -> Pagination:
        ...

    def all(self) -> list[JsonApiBaseModelMixin]:
        ...


class JsonApiError(Exception):
    """Exception wich will create a JSON:API error."""

    def __init__(self, id_or_error: t.Union[str, Exception, "JsonApiError", list["JsonApiError"]],
                 title: str | None = None, detail: str | None = None, code=None, status=None):
        if isinstance(id_or_error, str):
            code = str(code) or None
            status = str(status) or InternalServerError.code
            try:
                self.errors = [Error(id=id_or_error, code=code, title=title, detail=detail, status=status)]
            except ValidationError as e:
                self.errors = [Error(id=InternalServerError.code, title=str(title), detail=str(e),
                                     status=str(InternalServerError.code))]
        else:
            if isinstance(id_or_error, JsonApiError):
                id_or_error = [id_or_error]
            elif isinstance(id_or_error, Exception):
                self.errors = [Error(id=InternalServerError.code, title=type(id_or_error).__name__,
                                     detail=str(id_or_error), status=str(InternalServerError.code))]
            else:
                self.errors = id_or_error


class JsonApi:
    """Flask's extension implementing JSON:API specification.
    This extension uses the external API of ODOO.

    .. versionchanged:: 0.7.3
        ``env_var_prefix`` parameter may be a dict of bind values.
        GraphQL removed.
    """

    def __init__(self, app=None):
        """
        :param app: Flask application.
        """
        self.app = None

        if app:
            self.init_app(app)

    def init_app(self, app: TechMicroService):
        self.app = app
        handle_user_exception = app.handle_user_exception

        def _handle_user_exception(e):
            if 'application/vnd.api+json' not in request.headers.getlist('accept'):
                return handle_user_exception(e)

            if isinstance(e, ValidationError):
                app.full_logger_error(e)
                # noinspection PyTypedDict
                errors = [Error(id="", status=BadRequest.code, code=err['type'],
                                links=ErrorLinks(about=err['url']),
                                title=err['msg'], detail=str(err['loc'])) for err in e.errors()]
                errors.append(Error(id="", status=BadRequest.code, title=e.title, detail=str(e)))
                return self._toplevel_error_response(errors, status_code=BadRequest.code)

            try:
                rv = handle_user_exception(e)
                if isinstance(rv, HTTPException):
                    errors = [Error(id='0', title=rv.name, detail=rv.description, status=rv.code)]
                    return self._toplevel_error_response(errors, status_code=rv.code)
            except (Exception,):
                app.full_logger_error(e)
                if isinstance(e, JsonApiError):
                    return self._toplevel_error_response(e.errors)

            errors = [Error(id='0', title=e.__class__.__name__, detail=str(e), status=InternalServerError.code)]
            return self._toplevel_error_response(errors, status_code=InternalServerError.code)

        app.handle_user_exception = _handle_user_exception

        app.after_request(self._change_content_type)

    def _change_content_type(self, response):
        if 'application/vnd.api+json' not in request.headers.getlist('accept'):
            return response

        response.content_type = 'application/vnd.api+json'
        return response

    def _toplevel_error_response(self, errors, *, status_code=None):
        toplevel = TopLevel(errors=errors).model_dump_json()
        if status_code is None:
            status_code = max((err.status for err in errors))
        response = make_response(toplevel, status_code)
        response.content_type = 'application/vnd.api+json'
        return response


class FetchingContext:

    def __init__(self, include: str, fields__: dict[str, str], filters__: dict[str, str], sort: str | None = None,
                 page__number__: int | None = None, page__size__: int | None = None, page__max__: int | None = None):
        self.include = list(map(str.strip, include.split(','))) if include else []
        self._fields = fields__ if fields__ is not None else {}
        filters__ = filters__ if filters__ is not None else {}
        self._sort = list(map(str.strip, sort.split(','))) if sort else []
        self.page = page__number__
        self.per_page = page__size__
        self.max_per_page = page__max__

        self._filters: dict = {}
        for k, v in filters__.items():
            self._add_branch(self._filters, k.split('.'), v)

        self.connection_manager = contextlib.nullcontext()
        self.all_resources = ResourcesSet()

    def field_names(self, jsonapi_type) -> list[str]:
        if jsonapi_type in self._fields:
            fields = self._fields[jsonapi_type]
            if isinstance(fields, list):
                if len(fields) != 1:
                    msg = f"Wrong field value '{fields}' ; multiple fields parameter must be a comma-separated"
                    raise UnprocessableEntity(msg)
                field = fields[0]
            else:
                field = fields
            return list(map(str.strip, field.split(',')))
        return []

    def sql_filters(self, jsonapi_type, sql_model):
        """Returns the list of filters as a SQLAlchemy filter.

        :param jsonapi_type: the jsonapi type (used to get the filter parameters)
        :param sql_model: the SQLAlchemy model (used to get the SQLAlchemy filter)
        """
        filter_parameters = self._filters.get(jsonapi_type, {})

        _sql_filters = []
        for key, value in filter_parameters.items():
            column = getattr(sql_model, key, None)
            if column is None:
                msg = f"Wrong '{key}' property for sql model '{jsonapi_type}' in filters parameters"
                raise UnprocessableEntity(msg)
            if isinstance(column.property, ColumnProperty):
                _type = getattr(column, 'type', None)
                if _type and _type.python_type is bool:
                    if len(value) != 1:
                        msg = f"Multiple boolean values '{key}' property  for model '{jsonapi_type}' is not allowed"
                        raise UnprocessableEntity(msg)
                    _sql_filters.append(column == str_to_bool(value[0]))
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
                            condition = or_(condition, column.has(**{k: or_v}))
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
        toplevel.meta = meta


def jsonapi(func):
    """JSON:API decorator.
    Transforms an entry into an SQL entry with result as JSON:API.

    Must have Flask-SQLAlchemy extension installed.
    """

    def _jsonapi(*args, ensure_one: bool = False, include: str | None = None,
                 fields__: dict | None = None, filters__: dict | None = None, sort: str | None = None,
                 page__number__: int | None = None, page__size__: int | None = None, page__max__: int | None = None,
                 **kwargs):
        """

        :param args: entry args.,
                 page: int | None = None, per_page: int | None = None
        :param ensure_one: retrieves only one resource if true (default false).
        :param include:
        :param fields:
        :param filters:
        :param sort:
        :param page:
        :param per_page:
        :param max_per_page:
        :param kwargs: entry kwargs.
        """

        # set fetching context
        context = FetchingContext(include or [], fields__ or {}, filters__ or {}, sort,
                                  page__number__, page__size__, page__max__)
        setattr(request, 'fetching_context', context)

        # call entry
        query = func(*args, **kwargs)

        if not query:
            # Should change return lid for creation
            _toplevel = TopLevel(data=[]).model_dump_json(exclude_none=True)
        if isinstance(query, TopLevel):
            _toplevel = query
        else:
            _toplevel = asyncio.run(get_toplevel_from_query(query, ensure_one))
        return _toplevel.model_dump_json(exclude_none=True)

    # Adds JSON:API query parameters
    sig = signature(_jsonapi)
    # Removes self and kwargs from jsoapi wrapper
    jsonapi_sig = tuple(sig.parameters.values())[1:-1]
    sig = sig.replace(parameters=tuple(signature(func).parameters.values()) + jsonapi_sig)
    update_wrapper(_jsonapi, func)
    _jsonapi.__signature__ = sig
    return _jsonapi


class ResourcesSet(dict["JsonApiBaseModelMixin", dict]):
    """Set of resources for included part of TopLevel."""

    def extract(self, id, type) -> dict | None:
        for resource in self:
            if resource.jsonapi_type == type and resource.jsonapi_id == id:
                return self[resource]
        return None


def to_ressource_data(
        jsonapi_basemodel: JsonApiBaseModelMixin,
        toplevel_relationships: dict[JsonApiBaseModelMixin, dict[str, Relationship]]) -> dict[str, t.Any]:
    """Transform a simple pydantic data into a jsonapi ressource data.

    We cannot create directly the Resource here, as the data is not completed at this step
    and pydantic won't validate the non completed structure.
    """
    toplevel_relationships = toplevel_relationships or {}

    # set resource data from basemodel
    _type = jsonapi_basemodel.jsonapi_type
    data = jsonapi_basemodel.jsonapi_model_dump(fetching_context)
    if 'type' in data:
        _type = data.pop('type')
    else:
        _type = jsonapi_basemodel.jsonapi_type
    if 'id' in data:
        _id = data.pop('id')
    else:
        _id = jsonapi_basemodel.jsonapi_id

    # get relationships
    relationships: dict[str, list[dict[str, Relationship]]] = {}
    for key, value in {**data}.items():
        if isinstance(value, JsonApiBaseModelMixin):
            data.pop(key, None)
            add_relationship(key, value, relationships, toplevel_relationships)
        elif isinstance(value, list):
            for val in value:
                data.pop(key, None)
                if isinstance(val, JsonApiBaseModelMixin):
                    add_relationship(key, val, relationships, toplevel_relationships)
            continue
        else:
            continue

    link = Link(href=HttpUrl(jsonapi_basemodel.jsonapi_self_link))
    resource_data = {
        "type": _type,
        "id": _id,
        "lid": None,
        "attributes": data,
        "relationships": relationships,
        "links": {"self": link}
    }

    return resource_data


async def toplevel_from_basemodel(jsonapi_basemodel: JsonApiBaseModelMixin) -> TopLevel:
    assert isinstance(jsonapi_basemodel, JsonApiBaseModelMixin), "The returned value is not a JsonApiBaseModelMixin"
    ressource_data = to_ressource_data(jsonapi_basemodel, dict())
    flatten_relationships(ressource_data)
    included: list[Resource] = []
    if fetching_context.include:
        for key in fetching_context.include:

            # if the included resources is not in the fields
            if key not in ressource_data['relationships']:
                continue

            related = ressource_data['relationships'][key]
            if isinstance(related.data, list):
                for rel in related.data:
                    add_resource_to_included(rel, fetching_context.all_resources, included)
            else:
                add_resource_to_included(related.data, fetching_context.all_resources, included)

    try:
        return TopLevel(data=Resource(**ressource_data), included=included if included else None)
    except ValidationError as e:
        current_app.logger.error(e)
        raise


async def get_toplevel_from_query(query: Query, ensure_one) -> TopLevel:
    def get_toplevel():
        current_app.logger.debug(str(query))
        if ensure_one:
            toplevel = get_one_toplevel(query)
        else:
            toplevel = get_multi_toplevel(query)
        return toplevel

    # connection manager may be iterable
    if isinstance(fetching_context.connection_manager, t.Iterable):
        _toplevels = []
        for connection_manager in fetching_context.connection_manager:
            with connection_manager:
                _toplevels.append(await get_toplevel())
        data = [r for tp in _toplevels for r in tp.data]
        included = set((i for tp in _toplevels if tp.included for i in tp.included))
        _toplevel = TopLevel(data=data, included=included if included else None)
    else:
        with fetching_context.connection_manager:
            _toplevel = await get_toplevel()
    return _toplevel


async def get_multi_toplevel(query: Query) -> TopLevel:
    """Returns the multiple data top level resource from the query.
    """
    pagination = query.paginate(page=fetching_context.page, per_page=fetching_context.per_page,
                                max_per_page=fetching_context.max_per_page)
    toplevels: t.Iterable[TopLevel] = await asyncio.gather(
        *[toplevel_from_basemodel(p) for p in pagination]
    )
    data = [toplevel_to_resource(r) for r in toplevels]
    included = set((i for r in toplevels if r.included for i in r.included))
    toplevel = TopLevel(data=data, included=included if included else None)
    fetching_context.add_pagination(toplevel, pagination)
    return toplevel


async def get_one_toplevel(query: Query) -> TopLevel:
    """Returns the single top level resource from the query.

    :param query: the sql alchemy query.
    :param context: json:api fetching context.
    """
    resources: list[JsonApiBaseModelMixin] = query.all()
    if len(resources) != 1:
        raise NotFound("More than one resource found and ensure_one parameters was set")
    return await toplevel_from_basemodel(resources[0])


def toplevel_to_resource(toplevel: TopLevel) -> Resource:
    """Transform a toplevel structure into a jsonapi resource."""
    data = toplevel.data
    return Resource(type=data.type, id=data.id, attributes=data.attributes,
                    relationships=data.relationships, links=data.links)


def add_relationship(key: str, related_model: JsonApiBaseModelMixin,
                     relationships: dict[str, list[dict[str, Relationship]]],
                     toplevel_relationships: dict[JsonApiBaseModelMixin, dict[str, Relationship]]):
    """ Adds a relationship in the list of relationships from the related model.
    The relationship may not be complete for circular reference and will be completed after in construction.
    """

    def add_in_relationships(relationship):
        if key in relationships:
            relationships[key] = [*relationships[key], relationship]
        else:
            relationships[key] = [relationship]

    # if the related model was already referenced, just adds the already created relationship
    if related_model in toplevel_relationships:
        add_in_relationships(toplevel_relationships[related_model])

    # if the related model was not already referenced, creates a new relationssip
    else:
        relationship: dict[str, Relationship] = {}  # in process of creation so key is in list and dict will be updated
        toplevel_relationships[related_model] = relationship
        add_in_relationships(relationship)

        # get the related resource associated to the related model
        if related_model in fetching_context.all_resources:
            related_resource = fetching_context.all_resources[related_model]
        else:
            # creates and adds the related resource to the global list of included resources
            related_resource = to_ressource_data(related_model,
                                                 toplevel_relationships=toplevel_relationships)
            if fetching_context.include and key in fetching_context.include:
                fetching_context.all_resources[related_model] = related_resource

        # updates now the relationship once the process of creation is completed
        resource_identifier = ResourceIdentifier(id=related_resource['id'], type=related_resource['type'])
        relationship_link = RelationshipLinks(related=Link(href=HttpUrl(related_model.jsonapi_self_link)))
        relationship.update(Relationship(data=resource_identifier, links=relationship_link))


def flatten_relationships(data):
    """Transforms a list of relationships into a relationship with a list of related resources.
    """
    for key, relationships in data['relationships'].items():
        rel_data = [rel['data'] for rel in relationships]
        rel_links = [rel.get('links') for rel in relationships]
        if len(rel_data) == 1:
            rel_data = {"data": rel_data[0], "links": rel_links[0]}
        else:
            rel_data = {"data": rel_data}
            # rel_data = {"data": rel_data, "links": rel_links}
        data['relationships'][key] = Relationship(**rel_data)


def add_resource_to_included(relationship, all_resources, included):
    """Adds a resource in the included list.
    The resource is in gloabal resources set except if itself."""
    resource = all_resources.extract(type=relationship.type, id=relationship.id)
    if resource:
        flatten_relationships(resource)
        included.append(Resource(**resource))
