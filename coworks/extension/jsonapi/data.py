import typing as t


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

    def jsonapi_model_dump(self, context: "FetchingContext") -> dict[str, t.Any]:
        return {}


class JsonApiDict(dict, JsonApiDataMixin):
    """Dict data for JSON:API resource"""

    @property
    def jsonapi_type(self) -> str:
        return self['type']

    @property
    def jsonapi_id(self) -> str:
        return str(self['id'])

    def jsonapi_model_dump(self, context: "FetchingContext") -> dict[str, t.Any]:
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in self.items() if fields is None or k in fields}  # type:ignore


class JsonApiBaseModelMixin(JsonApiDataMixin):
    """Pydantic base model mixin as data for JSON:API resource"""

    def __hash__(self) -> int:
        return hash(self.jsonapi_type + str(self.jsonapi_id))

    def jsonapi_model_dump(self, context: "FetchingContext") -> dict[str, t.Any]:
        fields = context.field_names(self.jsonapi_type)
        return {k: v for k, v in self.model_dump().items() if fields is None or k in fields}  # type:ignore


class JsonApiDataSet(dict[JsonApiDataMixin, dict]):
    """Set of resources for included part of TopLevel."""

    def extract(self, *, type, id) -> dict | None:
        for resource in self:
            if resource.jsonapi_type == type and resource.jsonapi_id == id:
                return self[resource]
        return None
