.. _Blueprints:

Blueprints
==========

CoWorks blueprints are used to add to your application more routes deriving from logical components.
Blueprints allow you to complete your microservices with transversal functionalities.

Blueprint Registration
----------------------

Blueprints are defined as classes as microservice.

.. code-block:: python

	from coworks import Blueprint

	class Admin(Blueprint):

		def get_context(self):
			return self.current_request.to_dict()

This blueprint defines a new route ``context``. To add this route to your microservice, just register the
blueprint to the microservice.

.. code-block:: python

	app = SimpleExampleMicroservice()
	app.register_blueprint(Admin(), url_prefix="/admin")

The ``url_prefix`` parameter adds the prefix ``admin`` to the route ``context``.
Now the ``SimpleExampleMicroservice`` has a new route ``/admin/context``.

Predefined Blueprints
---------------------

Admin
^^^^^

The admin blueprint adds the following routes :

``/routes``

	List all the routes of the microservice with the signature extracted from its associated function.

``/context``

	Return the deploiement context of the microservice.



