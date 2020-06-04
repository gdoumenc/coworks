.. _tech_deployment:

TechMS Deployment
=================

CORS
----

For security reasons, by default microservices do not support CORS headers in response.

For simplicity, we can only add CORS parameters to all routes of the microservice.
To handle CORS protocol for a specific route, the ``OPTION`` method should be defined on that route.

To add CORS headers in all routes of the microservice, you can simply define ``allow_origin`` value in configuration::

	config = Config(cors=CORSConfig(allow_origin='*'))
	app = SimpleMicroService(app_name='test', config=config)

You can specify a single origin::

	config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
	app = SimpleMicroService(app_name='test', config=config)

Or a list::

	config = Config(cors=CORSConfig(allow_origin=['www.test.com', 'www.test.fr']))
	app = SimpleMicroService(app_name='test', config=config)

You can also specify other CORS parameters::

	config = Config(cors=CORSConfig(allow_origin='https://foo.example.com',
    					allow_headers=['X-Special-Header'],
    					max_age=600,
    					expose_headers=['X-Special-Header'],
    					allow_credentials=True))
	app = SimpleMicroService(app_name='test', configs=config)

As you can see, one configuration may be defined for a microservice. But we will explain below why a list of
configurations may be also defined.

Authorization
-------------

Class control
^^^^^^^^^^^^^

For simplicity, only one simple authorizer is defined per class. The authorizer may be defined by the method ``auth``.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			return True

The function must accept a single arg, which will be an instance of
`AuthRequest <https://chalice.readthedocs.io/en/latest/api.html#AuthRequest>`_.
If the method returns ``True`` all the routes are allowed. If it returns ``False`` all routes are denied.

Using the APIGateway model, the authorization protocol is defined by passing a token 'Authorization'.
The API client must include it in the header to send the authorization token to the Lambda authorizer.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			return auth_request.token == os.getenv('TOKEN')

*Note* : To define environment variables, see below.

To call this microservice, we have to put the right token in headers::

	curl https://zzzzzzzzz.execute-api.eu-west-1.amazonaws.com/my/route -H 'Authorization: thetokendefined'

If only certain routes are to be allowed, the authorizer must return a list of the allowed routes.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			if auth_request.token == os.getenv('ADMIN_TOKEN'):
				return True
			elif auth_request.token == os.getenv('USER_TOKEN'):
				return ['product/*']
			return False


*BEWARE* : Even if you don't use the token if the authorization method, you must define it in the header or the call
will be rejected by ``API Gateway``.

The `auth` function must also be defined at the bluprint level, and then it is available for all the bluprint rules.

Global control
^^^^^^^^^^^^^^

It is possible to redefine the class defined authorizer, by declaring a new authorization method in the configuration.
In this case, the authorizer is defined on all routes of the microservice.

Deploy vs update
----------------

Deployment and update are two important steps for the usage of the code. But we think these are different, so they are made
in two different ways

For deployment, we prefer using ``terraform`` and to update we will use ``cws``.


Stages
------

Staging is a very important part in the programmation development process.
You can easily deploy different stages of a microservice with APIGateway.

In the following, we will give an example of how to use `terraform` for staging.

Stagging with Terraform
^^^^^^^^^^^^^^^^^^^^^^^

We choose to implement staging with one lambda per stage and only one API for all the stages.
Other patterns may be used such as terraform workspace.

A Lambda per stage
******************

As we have seen, a configuration may be defined for a microservice. To implement several stages
we will use several configurations, one per stage.

.. code-block:: python

	DEV_CONFIG = Config(
		cors=CORSConfig(allow_origin='*'),
		environment_variables_file="dev_vars.json"
	)
	PROD_CONFIG = Config(
		workspace_name="prod",
		auth=my_auth,
		cors=CORSConfig(allow_origin='*'),
		environment_variables_file="prod_vars.secret.json",
		version="0.0"
	)

	WORKSPACES = [DEV_CONFIG, PROD_CONFIG]

Then you can initialize your microservice with those configurations, creating one lambda per
workspace configuration.

.. code-block:: python

	app = SimpleMicroService(app_name='app_name='test'', configs=WORKSPACES)

To run the microservice in a specific workspace, add the workspace parameter:

.. code-block:: python

	app.run(workspace='prod')

The complete microservice will be:

.. literalinclude:: ../tests/example/quickstart3.py

Staging deployment
******************

The terraform export can now be used to create one Lambda ressource per workspace:

.. code-block:: Terraform

	{% for stage in app_configs %}
	 	data "local_file" "environment_variables_{{ stage.workspace_name }}" {
	  		filename = "{{ project_dir }}/{{ stage.environment_variables_file }}"
	  	}
	  	resource "aws_lambda_function" "{{ res_id }}_{{ stage.workspace_name }}" {
	  		filename = local.lambda.zip_filename
			...
		}
	{% endfor %}

And an APIGateway deployment per workspace :

.. code-block:: Terraform

	{% for stage in app_configs %}
	  	resource "aws_api_gateway_deployment" "{{ res_id }}_{{ stage.workspace_name }}" {
			...
		}
	{% endfor %}

