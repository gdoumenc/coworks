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


class SlugMS(MS):
    slug = 'slug'

    def get(self):
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


class SlugParamMS(MS):
    slug = 'slug'

    def get(self, str):
        return str

    def get_concat(self, str1, str2):
        return str1 + str2
