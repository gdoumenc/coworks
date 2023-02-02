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
    the commands and options associated to the project.

**Execution configuration**
    As for the `Twelve-Factor App <https://12factor.net/>`_ : *"The twelve-factor app stores config in environment variables.
    Env vars are easy to change between deploys without changing any code;"*. Using environment variables is highly
    recommanded to enable easy code deployments to differents systems:
    Changing configuration is just updating variables in the configuration in the CI/CD process.

**Application configuration**
    At last : *"application config does not vary between deploys, and so is best done in the code."*

    That's why entries are defined in the code. The link from entry to function is always the same.

In Flask, there is only the concept of application configuration as the excution configuration if out of is scope
(mainly associated to the USWGI server).

In CoWorks, we use the concept of *stage* for execution configuration deployed in lambda variables.


Project configuration
---------------------

Stage is a key concept for the deployment. Stages are defined thru the concept of *workspace* in terraform, *stage* for
AWS API Gateway and *variables* of AWS Lambda.


Workspace definition
^^^^^^^^^^^^^^^^^^^^

The ``workspace`` value will correspond to the ``CWS_STAGE`` variable value.

You certainly may need to attach environment variables to your project. Of course thoses variables may depend on the
stage status. How? You just need to create and specify custom environment files.

CoWorks uses dotenv files to allow you to define your environment variables for stages.
Dotenv file are named ``.env`` and ``.env_{CWS_STAGE}``.

As example you can deploy the specific stage ``dev`` of the microservice ``app`` defined in the ``app`` python file
in the folder ``tech``::

    $ CWS_STAGE=dev deploy

The environment variables accessible from the lambda must be defined in ``.env`` and ``.env_dev``.

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
        commands:
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

By default all ``TechMicroService`` have access protection defined in the microservice itself and defined thru
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

