import asyncio
import contextlib
import typing as t
from functools import update_wrapper
from inspect import signature

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
from pydantic_core import ValidationError
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import NotFound

if t.TYPE_CHECKING:
    from flask_sqlalchemy.pagination import Pagination
    from flask_sqlalchemy.query import Query


class JsonApiError(Exception):
    """Exception wich will create a JSON:API error."""

    def __init__(self, id_or_error: t.Union[str, Exception, "JsonApiError", t.List["JsonApiError"]], title: str = None,
                 detail=None, code=None, status=None):
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

    def init_app(self, app):
        self.app = app
        handle_user_exception = app.handle_user_exception

        def _handle_user_exception(e):
            if 'application/vnd.api+json' not in request.headers.getlist('accept'):
                return handle_user_exception(e)

            if isinstance(e, ValidationError):
                self.app.full_logger_error(e)
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
                self.app.full_logger_error(e)
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


class ResourcesSet(dict["JsonApiBaseModelMixin", dict]):

    def extract(self, id, type) -> dict | None:
        for resource in self:
            if resource.jsonapi_type == type and resource.jsonapi_id == id:
                return self[resource]
        return None


class FetchingContext:

    def __init__(self, include: list[str], fields__: dict[str, str], filters__: dict[str, str], sort: str | None = None,
                 page__number__: int | None = None, page__size__: int | None = None, page__max__: int | None = None):
        self.include = include if include is not None else []
        self._fields = fields__ if fields__ is not None else {}
        filters__ = filters__ if filters__ is not None else {}
        self._sort = sort.split(',') if sort else []
        self.page = page__number__
        self.per_page = page__size__
        self.max_per_page = page__max__

        self._filters = {}
        for k, v in filters__.items():
            self._add_branch(self._filters, k.split('.'), v)

        self.connection_manager = contextlib.nullcontext()
        self.all_resources = ResourcesSet()

    def field_names(self, jsonapi_type) -> list[str]:
        if jsonapi_type in self._fields:
            fields = self._fields[jsonapi_type]
            field = fields[0] if isinstance(fields, list) else fields
            return field.split(',')
        return []

    def filters(self, jsonapi_type, model):
        tenant_filters = self._filters.get(jsonapi_type, {})

        sql_filters = []
        for key, value in tenant_filters.items():
            column = getattr(model, key)
            if column.type.python_type is bool:
                sql_filters.append(column == str_to_bool(value[0]))
            else:
                sql_filters.append(column.in_(value))
        return sql_filters

    def order_by(self, model):
        sql_order_by = []
        for key in self._sort:
            if key.startswith('-'):
                column = getattr(model, key[1:]).desc()
            else:
                column = getattr(model, key)
            sql_order_by.append(column)
        return sql_order_by

    def _add_branch(self, tree, vector, value):
        key = vector[0]

        if len(vector) == 1:
            tree[key] = value
        else:
            sub_tree = tree.get(key, {})
            tree[key] = self._add_branch(sub_tree, vector[1:], value)

        return tree

    @staticmethod
    def add_pagination(toplevel: TopLevel, pagination: "Pagination"):
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


class JsonApiBaseModelMixin:
    """Any model which may be transformed to JSON:API resource.
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

    def jsonapi_model_dump(self, context: FetchingContext) -> dict[str, t.Any]:
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in self.model_dump().items() if fields is None or k in fields}  # type:ignore


def to_ressource_data(jsonapi_basemodel: JsonApiBaseModelMixin, context: FetchingContext, *,
                      toplevel_relationships=None) -> dict[str, t.Any]:
    """Transform a simple data into a pydantic ressource data.

    We cannot create a Resource here, as the data is not completed at creation of the data.
    """
    toplevel_relationships = toplevel_relationships or {}
    # set resource data from basemodel

    _type = jsonapi_basemodel.jsonapi_type
    data = jsonapi_basemodel.jsonapi_model_dump(context)
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
            add_relationship(key, value, relationships, toplevel_relationships, context)
        elif isinstance(value, list):
            for val in value:
                data.pop(key, None)
                if isinstance(val, JsonApiBaseModelMixin):
                    add_relationship(key, val, relationships, toplevel_relationships, context)
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


async def toplevel_from_basemodel(jsonapi_basemodel: JsonApiBaseModelMixin, context: FetchingContext) -> TopLevel:
    assert isinstance(jsonapi_basemodel, JsonApiBaseModelMixin), "The returned value is not a JsonApiBaseModelMixin"
    ressource_data = to_ressource_data(jsonapi_basemodel, context)
    flatten_relationships(ressource_data)
    included: list[Resource] = []
    if context.include:
        for key in context.include:

            # if the included resources is not in the fields
            if key not in ressource_data['relationships']:
                continue

            related = ressource_data['relationships'][key]
            if isinstance(related.data, list):
                for rel in related.data:
                    add_resource_to_included(rel, context.all_resources, included)
            else:
                add_resource_to_included(related.data, context.all_resources, included)

    try:
        return TopLevel(data=Resource(**ressource_data), included=included if included else None)
    except ValidationError as e:
        current_app.logger.error(e)
        raise


def jsonapi(func):
    """JSON:API decorator.
    Transforms an entry into an SQL entry with result as JSON:API.

    Must have Flask-SQLAlchemy extension installed.
    """

    def _jsonapi(*args, ensure_one: bool = False, include: list[str] | None = None,
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
        context = FetchingContext(include or [], fields__ or {}, filters__ or {}, sort,
                                  page__number__, page__size__, page__max__)
        query_params = {'fetching': context}
        query = func(*args, **query_params, **kwargs)
        if not query:
            return TopLevel(data=[]).model_dump_json(exclude_none=True)
        with context.connection_manager:
            current_app.logger.debug(str(query))
            if ensure_one:
                toplevel = get_one_toplevel(query, context)
            else:
                toplevel = get_multi_toplevel(query, context)
            _toplevel = asyncio.run(toplevel)
        return _toplevel.model_dump_json(exclude_none=True)

    # Adds JSON:API query parameters
    sig = signature(_jsonapi)
    # Removes self and kwargs from jsoapi wrapper
    jsonapi_sig = tuple(sig.parameters.values())[1:-1]
    sig = sig.replace(parameters=tuple(signature(func).parameters.values()) + jsonapi_sig)
    update_wrapper(_jsonapi, func)
    _jsonapi.__signature__ = sig
    return _jsonapi


async def get_multi_toplevel(query: "Query", context: FetchingContext) -> TopLevel:
    pagination = query.paginate(page=context.page, per_page=context.per_page, max_per_page=context.max_per_page)
    resources: t.Iterable[TopLevel] = await asyncio.gather(
        *[toplevel_from_basemodel(p, context) for p in pagination]
    )
    data = [toplevel_to_resource(r) for r in resources]
    included = set((i for r in resources if r.included for i in r.included))
    toplevel = TopLevel(data=data, included=included if included else None)
    context.add_pagination(toplevel, pagination)
    return toplevel


async def get_one_toplevel(query: "Query", context: FetchingContext) -> TopLevel:
    """Returns the single top level resource from the query.

    :param query: the sql alchemy query.
    :param context: json:api fetching context.
    """
    resources: list[JsonApiBaseModelMixin] = query.all()
    if len(resources) != 1:
        raise NotFound("More than one resource found and ensure_one parameters was set")
    return await toplevel_from_basemodel(resources[0], context)


def toplevel_to_resource(toplevel: TopLevel) -> Resource:
    data = toplevel.data
    return Resource(type=data.type, id=data.id, attributes=data.attributes,
                    relationships=data.relationships, links=data.links)


def add_relationship(key: str, related: JsonApiBaseModelMixin, relationships: dict[str, list[dict[str, Relationship]]],
                     toplevel_relationships: dict[JsonApiBaseModelMixin, dict[str, Relationship]],
                     context: FetchingContext):
    """ Returns None if the resource is already referenced as a relationship.
    """
    if related in toplevel_relationships:
        if key in relationships:
            relationships[key] = [*relationships[key], toplevel_relationships[related]]
        else:
            relationships[key] = [toplevel_relationships[related]]
    else:
        relationship: dict[str, Relationship] = {}  # in process of creation so key is in list and dict will be updated
        toplevel_relationships[related] = relationship
        if key in relationships:
            relationships[key] = [*relationships[key], relationship]
        else:
            relationships[key] = [relationship]

        if related in context.all_resources:
            related_resource = context.all_resources[related]
        else:
            related_resource = to_ressource_data(related, context, toplevel_relationships=toplevel_relationships)
            if context.include and key in context.include:
                context.all_resources[related] = related_resource

        resource_identifier = ResourceIdentifier(id=related_resource['id'], type=related_resource['type'])
        relationshio_link = RelationshipLinks(related=Link(href=HttpUrl(related.jsonapi_self_link)))
        relationship.update(Relationship(data=resource_identifier, links=relationshio_link))


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
