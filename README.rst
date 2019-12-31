=======
CoWorks
=======

.. image:: https://travis-ci.com/gdoumenc/coworks.svg?branch=master
  :target: https://travis-ci.com/gdoumenc/coworks
  :alt: Travis CI
.. image:: https://readthedocs.org/projects/coworks/badge/?version=latest
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest
  :alt: Documentation Status

CoWorks is a Restful Microservice Framework on AWS based on Lambda, AWS Step Function and API Gateway products using Chalice microframework.

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
microservice in file `app.py`.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def get(self, usage="test"):
			return f"Simple microservice for {usage}.\n"

	app = SimpleExampleMicroservice("demo")

initialize the coworks project::

    $ cws init

Then make our microservice run locally::

    $ cws local
    Serving on http://127.0.0.1:8000
    127.0.0.1 - - [26/Dec/2019 18:29:11] "GET / HTTP/1.1" 200 -

Now test our microservice::

	$ curl http://127.0.1:8000
	Simple microservice for test.
	$ curl http://127.0.1:8000?usage=me
	Simple microservice for me.

Now complete it with more interface:

.. code-block:: python

	from collections import defaultdict
	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):
		values = defaultdict(int)

		def get(self, usage="test"):
			return f"Simple microservice for {usage}.\n"

		def get_value(self, index):
			return f"{self.values[index]}\n"

		def put_value(self, index, value=0):
			self.values[index] = value

	app = SimpleExampleMicroservice("demo")

Now test our completion::

	$ curl http://127.0.1:8000/value/123
	0
	$ curl -X PUT -d '{"value":456}' -H "Content-Type: application/json" http://127.0.1:8000/value/123
	null
	$ curl http://127.0.1:8000/value/123
	456
	$ curl -X PUT -d '789' -H "Content-Type: application/json" http://127.0.1:8000/value/123
	null
	$ curl http://127.0.1:8000/value/123
	789


Deploy this first simple microservice
-------------------------------------

Just deploy the microservice::

    $ pip freeze > requirements.txt
    $ cws deploy
	Creating deployment package.
	Updating policy for IAM role: simple-dev
	Updating lambda function: simple-dev
	Updating rest API
	Resources deployed:
	  - Lambda ARN: arn:aws:lambda:eu-west-1:760589174259:function:simple-dev
	  - Rest API URL: https://bd2ht6jc2m.execute-api.eu-west-1.amazonaws.com/dev/

Then test it::

	$ curl https://bd2ht6jc2m.execute-api.eu-west-1.amazonaws.com/dev/
	Simple microservice for test.

Delete it
---------

Just delete the microservice with ::

	$ cws delete

Related Projects
----------------

* `Chalice <https://github.com/aws/chalice>`__ - Python Serverless Microframework for AWS.


