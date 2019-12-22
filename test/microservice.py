from coworks import TechMicroService


class MS(TechMicroService):
    def __init__(self):
        super().__init__(app_name='test')


class SimpleMS(MS):

    def get(self):
        return "get"

    def get1(self):
        return "get1"

    def get_content(self):
        return "get_content"

    def post_content(self, value):
        return f"post_content {value}"

    def get_extended_content(self):
        return "hello world"


class PrefixedMS(MS):
    url_prefix = 'prefix'

    def get(self):
        return "hello world"

    def get_content(self):
        return "hello world"

    def get_extended_content(self):
        return "hello world"


class ParamMS(MS):
    value = "123"

    def get(self, str):
        return str

    def get_concat(self, str1, str2):
        return str1 + str2

    def get_value(self):
        return self.value

    def put_value(self):
        request = self.current_request
        self.value = request.json_body['value']
        return self.value


class PrefixedParamMS(MS):
    url_prefix = 'prefix'

    def get(self, str):
        return str

    def get_concat(self, str1, str2):
        return str1 + str2
