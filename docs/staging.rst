.. _staging:

Stages
======

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


