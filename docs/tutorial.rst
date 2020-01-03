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

The following function defines the GET method for the root service.

.. code-block:: python

	def get(self):
		...

The following function defines the GET method for the route ``service/test`` service.

.. code-block:: python

	def get_service_test(self):
		...

The following function defines the PUT method for the root service.

.. code-block:: python

	def put(self):
		...

URL Parameters
--------------

Query parameters
----------------

Test
----

Tests may be made in two manner:

* Classical test with test tools like pytest
* Online test (to be done)

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
