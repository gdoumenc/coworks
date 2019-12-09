from coworks import MicroService, Resource
import json

def test_app():
    ms = MicroService()

    class HelloWorld(Resource):
        def get(self):
            return {'hello': 'world'}

    ms.api.add_resource(HelloWorld, '/')

    event = {
        "httpMethod": "GET",
        'queryStringParameters': {
            'model': "product.product",
            "method": "search_read",
            "parameters": json.dumps([
                [[['default_code', 'ilike', ':MOR']]],
                {'fields': ['id', 'name', 'display_name']},
            ])
        },
    }

    res = ms.lambda_handler(event, {})

    assert(False)