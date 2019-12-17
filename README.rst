CoWorks
#######

Restful Microservice Framework on AWS based on Lambda, API Gateway and SQS products using Chalice microframework.

Each microservice is a small web application on the serverless Lambda product and offering restfull API interface
for use and a web dashboard for administration.

Using `Chalice <https://github.com/aws/chalice>`_ and ideas from `Flask-Classy <https://github.com/apiguy/flask-classy/>`_.

Installation
------------

Install the extension with::

    $ pip install coworks

Let's see how it works
----------------------

As a simple example is often more helpful and descriptive than a complete manual, lets write our first simple
microservice.

.. code-block:: python

    from collections import defaultdict
    from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):
		values = defaultdict(int)

		def get(self):
			return "Simple microservice for test."

		def get_value(self, index):
			return self.values[index]

		def put_value(self, index):
			request = self.current_request
			self.values[index] = request.json_body
			return self.values[index]


Then take a look to the ``test/test-example.py`` file to understand the behavior :

.. code-block:: python


	def test_simple_example(local_server_factory):
		local_server = local_server_factory(SimpleExampleMicroservice("example"))
		response = local_server.make_call(requests.get, '/')
		assert response.status_code == 200
		assert response.text == "Simple microservice for test."
		response = local_server.make_call(requests.get, '/value/1')
		assert response.status_code == 200
		assert response.text == "0"
		response = local_server.make_call(requests.put, '/value/1', json=1)
		assert response.status_code == 200
		assert response.text == "1"
		response = local_server.make_call(requests.get, '/value/1')
		assert response.status_code == 200
		assert response.text == "1"

Make a first complete simple microservice
-----------------------------------------

Create the project folder::

	$ mkdir simple
	$ cd simple
	$ pipenv install coworks
	$ pipenv shell
	(simple) $ cws init
	(simple) $ cat > app.py <<EOF
	from collections import defaultdict
	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):
    		values = defaultdict(int)

		def get(self):
			return "Simple microservice for test."

		def get_value(self, index):
			return self.values[index]

		def put_value(self, index):
			request = self.current_request
			self.values[index] = request.json_body
			return self.values[index]

	app = SimpleExampleMicroservice("simple")
	EOF
	(simple) $ cws local
	Serving on http://127.0.0.1:8000

In another terminal, just enter the following command::

	$ http http://127.0.0.1:8000
	HTTP/1.1 200 OK
	Content-Length: 29
	Content-Type: application/json
	Date: Tue, 17 Dec 2019 11:53:26 GMT
	Server: BaseHTTP/0.6 Python/3.7.2

	Simple microservice for test.

.. note:: If http command is not defined, enter : ``sudo apt install httpie``.