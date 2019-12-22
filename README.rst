=======
CoWorks
=======

.. image:: https://travis-ci.com/gdoumenc/coworks.svg?branch=master
   :target: https://travis-ci.com/gdoumenc/coworks
   :alt: Travis CI

Restful Microservice Framework on AWS based on Lambda, AWS Step Functions, API Gateway products using Chalice microframework.

Each microservice is a small web application on the serverless Lambda product and offering restfull API interface
for use and a web dashboard for administration.

Using and derived from `Chalice <https://github.com/aws/chalice>`_ and ideas from `Flask-Classy <https://github.com/apiguy/flask-classy/>`_.

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

	$ http http://127.0.0.1:8000/value/1
	HTTP/1.1 200 OK
	Content-Length: 1
	Content-Type: application/json
	Date: Tue, 17 Dec 2019 12:11:47 GMT
	Server: BaseHTTP/0.6 Python/3.7.2

	0

	$ echo 123 | http put http://127.0.0.1:8000/value/1
	HTTP/1.1 200 OK
	Content-Length: 1
	Content-Type: application/json
	Date: Tue, 17 Dec 2019 12:14:58 GMT
	Server: BaseHTTP/0.6 Python/3.7.2

	123

	$ http http://127.0.0.1:8000/value/1
	HTTP/1.1 200 OK
	Content-Length: 1
	Content-Type: application/json
	Date: Tue, 17 Dec 2019 12:15:02 GMT
	Server: BaseHTTP/0.6 Python/3.7.2

	123

.. note:: If http command is not defined, enter : ``sudo apt install httpie``.

Deploy this first simple microservice
-------------------------------------

Just deploy the microservice::

    $ pipenv lock -r > requirements.txt
    $ cws deploy
	Creating deployment package.
	Updating policy for IAM role: simple-dev
	Updating lambda function: simple-dev
	Updating rest API
	Resources deployed:
	  - Lambda ARN: arn:aws:lambda:eu-west-1:760589174259:function:simple-dev
	  - Rest API URL: https://gtvlc2utih.execute-api.eu-west-1.amazonaws.com/api/

Then test it::

	$ http https://gtvlc2utih.execute-api.eu-west-1.amazonaws.com/api
	HTTP/1.1 200 OK
	Connection: keep-alive
	Content-Length: 29
	Content-Type: application/json
	Date: Tue, 17 Dec 2019 12:34:34 GMT
	Via: 1.1 f41c2361062c4fc74c645f4e4fddd2de.cloudfront.net (CloudFront)
	X-Amz-Cf-Id: o8vqUBeoKZOBH88AM29lW7carQe07YHGwmq6busPfn0kbL0kwJE1GQ==
	X-Amz-Cf-Pop: CDG3-C2
	X-Amzn-Trace-Id: Root=1-5df8cb5a-14960a80746ff3e450d54874;Sampled=0
	X-Cache: Miss from cloudfront
	x-amz-apigw-id: E2S2KHuYDoEFltg=
	x-amzn-RequestId: d209b85e-5c2a-4fca-b1d6-e785052c0c3d

	Simple microservice for test.

Delete it
---------

Just delete the microservice with ::

	$ cws delete

Related Projects
----------------

* `Chalice <https://github.com/aws/chalice>`__ - Python Serverless Microframework for AWS.


