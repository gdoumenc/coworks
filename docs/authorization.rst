.. _authorization:

Authorization
=============

Simple control
--------------

In CoWorks, only one simple authorizer is defined per class. The authorizer is defined by the method `auth`.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			return True

The function must accept a single arg, which will be an instance of `AuthRequest <https://chalice.readthedocs.io/en/latest/api.html#AuthRequest>`_.
If the method returns ``True`` all the routes are allowed. If it returns ``False`` all routes are denied.

Using the APIGateway model, the authorization protocol is defined by passing a token 'authorization'.
The API client must include a header of this name to send the authorization token to the Lambda authorizer.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			return auth_request.token == os.getenv('TOKEN')


To call this microservice, we have to put the right token in header::

	http https://qmk6utp3mh.execute-api.eu-west-1.amazonaws.com/dev/product/0301-100 'authorization: thetokendefined'

If only some routes are allowed, the authorizer must return a list of the allowed routes.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			if auth_request.token == os.getenv('ADMIN_TOKEN'):
				return True
			elif auth_request.token == os.getenv('USER_TOKEN'):
				return ['product/*']
			return False


**BEWARE** : Even if you don't use the token, if the authorizatin method is defined, you must define an authorization token in the header or the call
will be rejected.


Composed control
----------------

There are two kinds of authorization defined in ``CoWorks``

* Execution rights for microservice,
* Access control on resources.

For composition of microservices, it is very annoying to have as many token as microservices used.
Especially when you have many tokens for execution rights (allowing respectively admin mode, debug information, ...)
and resource access control (read only, complete access, ..)

To be completed.
