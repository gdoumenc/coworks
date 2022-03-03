.. _configuration:

Configuration
=============

Configuration versus Environment variable
-----------------------------------------

There are three configuration levels:

    * Project config,
    * Execution config,
    * Application config.

**Project configuration**
    Project configuration is related to how the team works and how deployment should be done. This description
    is done by a project configuration file: ``project.cws.yml``. This project configuration file describes
    the commands and options associated on the project.

**Execution configuration**
    As for the `Twelve-Factor App <https://12factor.net/>`_ : *"The twelve-factor app stores config in environment variables.
    Env vars are easy to change between deploys without changing any code;"*. Using environment variables is highly
    recommanded to enable easy code deployments to differents systems:
    Changing configuration is just updating variables in the configuration in the CI/CD process.

**Application configuration**
    At last : *"application config does not vary between deploys, and so is best done in the code."*

    That's why entries are defined in the code. The link from entry to function is always the same.

Project configuration
---------------------

Stage is a key concept for the deployment. Stages are defined thru the concept of workspace (same as for terraform).


Workspace definition
^^^^^^^^^^^^^^^^^^^^

To add a workspace and its configuration to a microservice, defined it and use it with the ``configs`` parameter in its
constructor::

	config = Config(workspace='local', environment_variables_file=Path("config") / "vars_local.json")
	app = SimpleMicroService(ms_name='test', configs=config)

The ``workspace`` value will correspond to the ``--workspace`` argument for the commands ``run`` or ``deploy``.

In the exemple over, if you run the microservice in the workspace ``local``, then environment file will be found in
``config/vars_local.json``.

You can then define several configurations::

	local_config = Config(workspace='local', environment_variables_file=Path("config") / "vars_local.json")
	dev_config = Config(workspace='dev', environment_variables_file=Path("config") / "vars_dev.json")
	app = SimpleMicroService(ms_name='test', configs=[local_config, dev_config])

This allows you to define specific environment values for local running and for dev deploied stages.

Three predefined workspace configurations are defined:

    * ``LocalConfig`` for local development run.
    * ``DevConfig`` for deployed development version with trace.
    * ``ProdConfig``. This configuration class is defined for production workspace where their names are version names, i.e. defined as ``r"v[1-9]+"``.

Project configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^

A project configuration file is a YAML file containg the command and options defined for the project.

Example
*******

Example of a `project.cws.yml` file:

.. code-block:: yaml

    version: 3
    commands:
      run:
        host: localhost
        port: 5000
      deploy:
        class: fpr.cws.deploy.fpr_deploy
        profile_name: fpr-customer
        bucket: coworks-microservice
        customer: neorezo
        project: cws_utils_mail
        layers:
          - arn:aws:lambda:eu-west-1:935392763270:layer:coworks-0.6.8
    workspaces:
      dev:
        run:
          port: 8000
        deploy:
          layers:
            - arn:aws:lambda:eu-west-1:935392763270:layer:coworks-dev

Structure
*********

.. list-table:: **Project Configuration File Structure**
   :widths: 10 20 20
   :header-rows: 1

   * - Field
     - Value
     - Description
   * - version
     - 3
     - YAML syntax version
   * - commands
     - Command Structure List (below)
     - List of commands
   * - workspaces
     - Workspace Structure List (below)
     - List of workspaces where commands are redefined

.. list-table:: **Command Structure**
   :widths: 10 10 10
   :header-rows: 1

   * - Command Name
     - Command Option
     - Project Value
   * - run
     -
     -
   * -
     - host
     - localhost
   * -
     - port
     - 5000

.. list-table:: **Workspace Structure**
   :widths: 10 10 10 10
   :header-rows: 1

   * - Workspace Name
     - Command Name
     - Command Option
     - Project Value
   * - dev
     -
     -
     -
   * -
     - run
     -
     -
   * -
     -
     - port
     - 8000


.. _auth:

Authorization
-------------

By default all  ``TechMicroService`` have access protection defined in the microservice itself.and defined thru
a token basic authentication protocol based on
`HTTP Authentification  <https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication>`_

Class control
^^^^^^^^^^^^^

For simplicity, we can define only one simple authorizer on a class. The authorizer may be defined by the method
``token_authorizer``.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def token_authorizer(self, token):
			return True

If the method returns ``True`` all the routes are allowed. If it returns ``False`` all routes are denied.

Using the APIGateway model, the authorization protocol is defined by passing a token 'Authorization'.
The API client must include it in the header to send the authorization token to the Lambda authorizer.

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def token_authorizer(self, token):
			return token == os.getenv('TOKEN')

To call this microservice, we have to put the right token in headers::

	curl https://zzzzzzzzz.execute-api.eu-west-1.amazonaws.com/my/route -H 'Authorization: thetokendefined'

