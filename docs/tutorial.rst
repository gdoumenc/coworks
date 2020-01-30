.. _tutorial:

Tutorial
========

Representational state transfer (REST) is a software architectural style that defines a set of constraints to be used for creating Web services.
CoWorks microservices conform to the REST architectural style, and are so-called RESTful Web services.

Routing
-------

Routes are defined by function names in the microservice class.
The function names must follow the syntax below::

	<request_method><associated_route>

The request method is then defined for the associated route.
Composed routes are defined thru the ``_`` separator.

Examples
^^^^^^^^

The following function defines the GET method for the root of the microservice:

.. code-block:: python

	def get(self):
		return "root"

The following function defines the GET method for the route ``service/test``:

.. code-block:: python

	def get_service_test(self):
		return "test"

The following function defines the PUT method for the root of the microservice:

.. code-block:: python

	def put(self):
		return put


Entrypoint Parameters
---------------------

URL Parameters
^^^^^^^^^^^^^^

You can define entrypoint function arguments as part of the URL:

.. code-block:: python

	def get_content(self, index):
		return f"get content {index}"

This defines a route which first part is the fixed string ``content`` and the second part is the ``index`` value.
We denote the route like this::

	/content/{index}

You can have several positionnal parameters (ordered from the URL path):

.. code-block:: python

	def get_content(self, bucket, key1, key2, key3):
		return f"get content of {bucket} with key {key1/key2/key3}"

which defines the route ``/content/{bucket}/{key1}/{key2}/{key3}``.

*Note*: In this case, the keys parameters must not have the ``/`` character.

You can also construct more complex routes from different parameters:

.. code-block:: python

	def get_content(self):
		return "get content"

	def get_content_(self, value):
		return f"get content with {value}"

	def get_content__(self, value, other):
		return f"get content with {value} and {other}"

This defines the respecting following routes::

	/content
	/content/{value}
	/content/{value}/{other}

This is usefull for offering a CRUD microservice:

.. code-block:: python

	def get(self):
		return "the list of instances of a model"

	def get_(self, id):
		return f"the instance with id {id}"

	def put(self, data):
		return f"creates a new instance with {data}"

	def put_(self, id, data):
		return f"modifies an instance identified by {id} with {data}"


Query or body parameters
^^^^^^^^^^^^^^^^^^^^^^^^

You can define default parameters to your entrypoint function.
In that case the value of those default parameters are defined by query parameters or JSON body content.

.. code-block:: python

	def get_content(self, id=None, name=""):
		return f"the instance with id {id} and/or name {name}"

Where the ``id`` parameter can be defined by the query parameter::

	/content?id=32&name=test

Or in python code using the ``requests`` module::

	requests.get("/content", params={"id": 32, "name": "test"})

or by a JSON structure::

	request.get(""/content", json={"id": 32, "name": "test"}")

A list parameter can be defined by a multi value parameter::

	/content?id=32&name=test&name=other

Which is equivalent to the JSON call::

	request.get(""/content", json={"id": 32, "name": ["test", "other"]}")



**Note**: The current implementation doesn't take in account the typing of the entrypoint function parameters (forcasted).
So all query paramerters are from type ``string``.
If you want to pass typed or structured values, use the JSON mode.

You can also use the ``**`` notation to get any values::

	def get_content(self, **kwargs):
		return f"here are all the parameters: {kwargs}"


Microservice Response
---------------------

As for ``Flask`` and ``Chalice``, the return value from a class microservice is automatically converted into a response object for you.

* If the return value is a ``string`` or ``bytes``, it’s converted into a response object with the string or bytes list as response body, a 200 OK status code and a text/html mimetype.
* If the return value is a ``dict`` or a ``list``, it's converted to a JSON structure.
* If a ``tuple`` is returned the items in the tuple can provide extra information. Such tuples have to be in the form (response, status), or (response, status, headers). The status value will override the status code and headers can be a list or dictionary of additional header values.

If none of that works, ``CoWorks`` will assume the return value is a valid ``Chalice`` `Response <https://chalice.readthedocs.io/en/latest/api.html#Response>`_. instance.

Test
----

Tests may be made in two manner:

* Online test
* Classical test with test tools like pytest

As a classical python application
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As seen, you can run your microservice on local with the command::

	$ cws local

You can also run you microservice in a classical manner of python application:

.. code-block:: python

	if __name__ == '__main__':
		app.run()

You can add more options for testing as changing the port or the stage::

	$ cws local --stage prod --port 8001

Then same for python application:

.. code-block:: python

	if __name__ == '__main__':
		app.run(stage="prod", port=8001)

To get the list of options::

	$ cws local --help

PyTest
^^^^^^

To create your tests for pytest, add this fixture in your ``conftest.py``::

	from coworks.pytest.fixture import local_server_factory

Then

.. code-block:: python

	def test_root(local_server_factory):
		local_server = local_server_factory(SimpleExampleMicroservice())
		response = local_server.make_call(requests.get, '/')
		assert response.status_code == 200

If you want to debug your test and stop on breakpoint, you need to give more time to the request for timeout:

.. code-block:: python

	def test_root(local_server_factory):
		local_server = local_server_factory(SimpleExampleMicroservice())
		response = local_server.make_call(requests.get, '/', timeout=200.0)
		assert response.status_code == 200

If you have an authorized access:

.. code-block:: python

	def test_root(local_server_factory):
		local_server = local_server_factory(SimpleExampleMicroservice())
		response = local_server.make_call(requests.get, '/', headers={'authorization': 'allow'})
		assert response.status_code == 200
