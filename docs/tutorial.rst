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

