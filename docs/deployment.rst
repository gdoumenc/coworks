.. _deployment:

Deployment
==========

Authorization
-------------

Simple control
^^^^^^^^^^^^^^

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


**BEWARE** : Even if you don't use the token if the authorizatin method, you must define it in the header or the call
will be rejected.


Fine grained control
^^^^^^^^^^^^^^^^^^^^


** TO BE COMPLETED **


Stages
------

Staging is a very important part in the programmation development process.
You can easily deploy different stages of a microservice with APIGateway.

For that purpose, we prefer using ``terraform`` for deploying microservices than ``chalice``.
Nevertheless, we will explain first how stagging with ``chalice``

Stagging with Chalice
^^^^^^^^^^^^^^^^^^^^^

Creating a new stage
********************

By default, when the project is initialized, a stage ``dev`` is created.
This stage is defined in the file ``.chalice/config.json``:

.. code-block:: json

	{
	  "version": "2.0",
	  "app_name": "example",
	  "stages": {
		"dev": {
		  "api_gateway_stage": "dev",
		  "environment_variables": {
			"test": "test environment variable"
		  }
		}
	  }
	}

If you want to define a new stage ``prod``, then just adds it in this file as follow:

.. code-block:: json

	{
	  "version": "2.0",
	  "app_name": "example",
	  "stages": {
		"dev": {
		  "api_gateway_stage": "dev",
		  "environment_variables": {
			"test": "test environment variable"
		  }
		},
		"prod": {
		  "api_gateway_stage": "prod",
		  "environment_variables": {
			"test": "prod variable"
		  }
		}
	  }
	}

As you can see we have changed the ``api_gateway_stage`` value to create a new entry point in our API.
We also have defined a different value for the environment variable ``test``.

If you want to share a same environment variable for any stage, do the following:

.. code-block:: json

	{
	  "version": "2.0",
	  "app_name": "example",
	  "environment_variables": {
	    "global": "same variable for any stage"
	  },
	  "stages": {
		"dev": {
		  "api_gateway_stage": "dev",
		  "environment_variables": {
			"test": "test environment variable"
		  }
		},
		"prod": {
		  "api_gateway_stage": "prod",
		  "environment_variables": {
			"test": "prod variable"
		  }
		}
	  }
	}

We strongly recommand to have a stage per branch from your versionning process.


Staging deployment
******************

The deployment informations on a stage are defined in the file ``.chalice/deployed/{stage}.json``.

We can then use the same APIGateway to implement the different stages reusing the ``rest_api_id value``.

	$ cws deploy --stage master --rest_api_id dev

(not done for now have to change the ``rest_api_url`` directly in the ``.chalice/deployed/master.json`` file::

      "name": "rest_api",
      "resource_type": "rest_api",
      "rest_api_id": "qmk6utp3mh",
      "rest_api_url": "https://qmk6utp3mh.execute-api.eu-west-1.amazonaws.com/prod/"

Then we can use a genric URL for calling a specific stage of this microservice::

	https://qmk6utp3mh.execute-api.eu-west-1.amazonaws.com/{stage}

Stagging with Terraform
^^^^^^^^^^^^^^^^^^^^^^^

** TO BE COMPLETED **


Blueprints and Extensions
-------------------------

Blueprints
^^^^^^^^^^

CoWorks blueprints are used to add to your application more routes deriving from logical components.
Blueprints allow you to complete your microservices with transversal functionalities.

Blueprint Registration
**********************

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
*********************

Admin
:::::

The admin blueprint adds the following routes :

``/routes``

	List all the routes of the microservice with the signature extracted from its associated function.

``/context``

	Return the deploiement context of the microservice.

Extensions
^^^^^^^^^^

Extensions are extra packages that add functionality to a CoWorks application.
Extensions are inspired from `Flask <https://flask.palletsprojects.com/en/1.1.x/extensions/>`_.


Predefined Extensions
*********************

Writer
::::::

Writers are extensions used by the ``format`` option of the ``cws export`` command. It uses Jinja templating to
generate service description.

OpenAPI writer
::::::::::::::

Considering the test/exammple in the source, you can generate the OpenAPI file description with the follong command :

.. code-block:: shell

	cws export -m example -f openapi

