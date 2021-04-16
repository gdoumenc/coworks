.. _configuration:

Configuration
=============

Configuration versus Environment variable
-----------------------------------------

We can consider three configuration levels:

    * project config,
    * execution config,
    * application config.

Project configuration is related to how the team works and how deployment should be done. This description
is done by a project configuration file: ``project.cws.yml``. This project configuration file describes :

    * the miscroservices declared
    * the commands and options associated on those microservices

As for the `Twelve-Factor App <https://12factor.net/>`_ : *"The twelve-factor app stores config in environment variables.
Env vars are easy to change between deploys without changing any code;"*. Using environment variables is highly
recommanded to enable easy code deployments to differents systems:
Changing configuration is just updating variables in the configuration in the CI/CD process.

At last : *"application config does not vary between deploys, and so is best done in the code."* That's why
entries are defined in the code.

Workspace configuration
-----------------------

To add an workspace configuration to a microservice, defined it and use it with the ``configs`` parameter in its
constructor::

	config = Config(workspace='local', environment_variables_file=Path("config") / "vars_local.json")
	app = SimpleMicroService(ms_name='test', configs=config)

The ``workspace`` value will correspond to the ``--workspace`` argument for the commands ``run`` or ``deploy``.

In this case, if you run the microservice in the workspace ``local``, then environment file will be found in
``config/vars_local.json``.

You can then define several configurations::

	local_config = Config(workspace='local', environment_variables_file=Path("config") / "vars_local.json")
	dev_config = Config(workspace='dev', environment_variables_file=Path("config") / "vars_dev.json")
	app = SimpleMicroService(ms_name='test', configs=[local_config, dev_config])

This allows you to define specific environment values for local running and for dev deploied stage.

The ``Config`` class is defined as::

    @dataclass
    class Config:
        """ Configuration class for deployment."""

        workspace: str = DEFAULT_WORKSPACE
        environment_variables_file: Union[str, List[str]] = 'vars.json'
        environment_variables: Union[dict, List[dict]] = None
        auth: Callable[[CoworksMixin, AuthRequest], Union[bool, list, AuthResponse]] = None
        cors: CORSConfig = CORSConfig(allow_origin='')
        content_type: Tuple[str] = ('multipart/form-data', 'application/json', 'text/plain')

Three other global workspace parameters may be defined and are describe below.

Another usefull class defined is ``ProdConfig``. This configuration class is defined for production workspace
where their names are version names, i.e. defined as ``r"v[1-9]+"``.

CORS
----

For security reasons, by default microservices do not support CORS headers in response.

For simplicity, we can only add CORS parameters to all routes of the microservice.
To handle CORS protocol for a specific route, the ``OPTION`` method should be defined on that route and will override
the global parameter.

To add CORS headers in all routes of the microservice, you can simply define ``allow_origin`` value in configuration::

	config = Config(cors=CORSConfig(allow_origin='*'))
	app = SimpleMicroService(ms_name='test', config=config)

You can specify a single origin::

	config = Config(cors=CORSConfig(allow_origin='www.test.fr'))
	app = SimpleMicroService(ms_name='test', config=config)

Or a list::

	config = Config(cors=CORSConfig(allow_origin=os.getenv('ALLOW_ORIGIN', '*').split(','))
	app = SimpleMicroService(ms_name='test', config=config)

*Note*: Even if the configuration is defined in the code, we recommend that some CORS parameters as ``allow-origin``
should be defined in environment.

You can also specify other CORS parameters::

	config = Config(cors=CORSConfig(allow_origin='https://foo.example.com',
    					allow_headers=['X-Special-Header'],
    					max_age=600,
    					expose_headers=['X-Special-Header'],
    					allow_credentials=True))
	app = SimpleMicroService(ms_name='test', configs=config)



.. _auth:

Authorization
-------------

Class control
^^^^^^^^^^^^^

For simplicity, we can define one simple authorizer on a class. The authorizer may be defined by the method ``auth``.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def auth(self, auth_request):
			return True

*Note*: This method may be static or not.

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

Content type
------------
