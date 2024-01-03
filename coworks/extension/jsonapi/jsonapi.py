import asyncio
import typing as t
from functools import update_wrapper
from inspect import signature

from coworks import TechMicroService
from coworks import request
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
from werkzeug.exceptions import BadRequest
from werkzeug.exceptions import HTTPException
from werkzeug.exceptions import InternalServerError
from werkzeug.exceptions import NotFound

from .data import JsonApiDataMixin
from .fetching import create_fetching_context_proxy
from .fetching import fetching_context
from .query import Query


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
                errors = [Error(id="", status=BadRequest.code, code=err['type'],
                                links=ErrorLinks(about=err['url']),  # type: ignore[typeddict-item]
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

        app.handle_user_exception = _handle_user_exception  # type: ignore[method-assign]

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
        create_fetching_context_proxy(include, fields__, filters__, sort, page__number__, page__size__, page__max__)
        res = func(*args, **kwargs)
        if isinstance(res, Query):
            _toplevel = asyncio.run(get_toplevel_from_query(res, ensure_one))
        elif isinstance(res, TopLevel):
            _toplevel = res
        else:
            _toplevel = TopLevel(data=[])
        return _toplevel.model_dump_json(exclude_none=True)

    # Adds JSON:API query parameters
    sig = signature(_jsonapi)
    # Removes self and kwargs from jsoapi wrapper
    jsonapi_sig = tuple(sig.parameters.values())[1:-1]
    sig = sig.replace(parameters=tuple(signature(func).parameters.values()) + jsonapi_sig)
    update_wrapper(_jsonapi, func)
    setattr(_jsonapi, '__signature__', sig)
    return _jsonapi


def to_ressource_data(jsonapi_basemodel: JsonApiDataMixin,
                      toplevel_relationships: dict[JsonApiDataMixin, dict[str, Relationship]]) -> dict[str, t.Any]:
    """Transform a simple structure data into a jsonapi ressource data.

    We cannot create directly the Resource here, as the data is not completed at this step
    and pydantic won't validate the non completed structure.
    """

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
    toplevel_relationships = toplevel_relationships or {}
    relationships: dict[str, list[dict[str, Relationship]]] = {}
    for key, value in {**data}.items():
        if isinstance(value, JsonApiDataMixin):
            data.pop(key, None)
            add_relationship(key, value, relationships, toplevel_relationships)
        elif isinstance(value, list):
            for val in value:
                if isinstance(val, JsonApiDataMixin):
                    data.pop(key, None)
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


async def toplevel_from_basemodel(jsonapi_basemodel: JsonApiDataMixin) -> TopLevel:
    assert_msg = f"The base model '{jsonapi_basemodel}' is not a JsonApiDataMixin"
    assert isinstance(jsonapi_basemodel, JsonApiDataMixin), assert_msg

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


async def get_toplevel_from_query(query: Query, ensure_one: bool) -> TopLevel:
    """Returns the Toplevel structure from the query."""

    def get_toplevel():
        current_app.logger.debug(str(query))
        if ensure_one:
            toplevel = get_one_toplevel(query)
        else:
            toplevel = get_multi_toplevel(query)
        return toplevel

    # connection manager may be iterabl (must be performed asynchronously)
    if isinstance(fetching_context.connection_manager, t.Iterable):
        _toplevels = []
        for connection_manager in fetching_context.connection_manager:
            with connection_manager:
                _toplevels.append(await get_toplevel())
        data = [r for tp in _toplevels for r in tp.data]
        included = set((i for tp in _toplevels if tp.included for i in tp.included))
        return TopLevel(data=data, included=included if included else None)

    with fetching_context.connection_manager:
        return await get_toplevel()


async def get_multi_toplevel(query: Query) -> TopLevel:
    """Returns the multiple data top level resource from the query.
    """
    pagination = query.paginate(page=fetching_context.page, per_page=fetching_context.per_page,
                                max_per_page=fetching_context.max_per_page)
    toplevels: t.Iterable[TopLevel] = await asyncio.gather(
        *[toplevel_from_basemodel(p) for p in pagination]
    )
    toplevel = merge_toplevels(toplevels)
    fetching_context.add_pagination(toplevel, pagination)
    return toplevel


async def get_one_toplevel(query: Query) -> TopLevel:
    """Returns the single top level resource from the query.

    :param query: the sql alchemy query.
    """
    resources: list[JsonApiDataMixin] = query.all()
    if len(resources) != 1:
        raise NotFound("None or more than one resource found and ensure_one parameters was set")
    return await toplevel_from_basemodel(resources[0])


def toplevel_to_resource(toplevel: TopLevel) -> Resource:
    """Transform a toplevel into a jsonapi resource."""
    data = toplevel.data
    return Resource(type=data.type, id=data.id, attributes=data.attributes,
                    relationships=data.relationships, links=data.links)


def merge_toplevels(toplevels: t.Iterable[TopLevel]) -> TopLevel:
    """Combines toplevels in one toplevel."""
    data = [toplevel_to_resource(r) for r in toplevels]
    included = set((i for r in toplevels if r.included for i in r.included))
    return TopLevel(data=data, included=included if included else None)


def add_relationship(key: str, related_model: JsonApiDataMixin,
                     relationships: dict[str, list[dict[str, Relationship]]],
                     toplevel_relationships: dict[JsonApiDataMixin, dict[str, Relationship]]):
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
            rel = {"data": rel_data[0]}
            # rel = {"data": rel_data[0], "links": rel_links[0]}
        else:
            rel = {"data": rel_data}
            # rel = {"data": rel_data, "links": rel_links}
        data['relationships'][key] = Relationship(**rel)


def add_resource_to_included(relationship, all_resources, included):
    """Adds a resource in the included list.
    The resource is in global resources set except if itself."""
    resource = all_resources.extract(type=relationship.type, id=relationship.id)
    if resource:
        flatten_relationships(resource)
        included.append(Resource(**resource))
