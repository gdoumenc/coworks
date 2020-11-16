.. _command:

Commands
========

Coworks allows you to extends the ``cws`` applications with commands. This powerfull extension is very usefull
for complex deployment, testing or documentation.

As explained before, the microservice architecture needs to be completed by tools. The cws command line ``cws`` is
the interface for that purpose.

.. _cli:

CWS : Command Line Interface
----------------------------

cws
^^^

``cws`` is a command-line shell program that provides convenience and productivity
features to help user to :

 * Get microservices informations,
 * Export microservices to another formats,
 * Update deployed microservices,
 * ...

It is a generic client interface on which commands may be defined.

Usage
^^^^^

To view a list of the available commands at any time, just run `cws` with no arguments::

	$ cws
    Usage: cws [OPTIONS] COMMAND [ARGS]...

    Options:
      --version               Show the version and exit.
      -p, --project-dir TEXT  The project directory path (absolute or relative).
                              Defaults to CWD

      -m, --module TEXT       Filename of your microservice python source file.
      -s, --service TEXT      Coworks application in the source file.
      -w, --workspace TEXT    Application stage.
      --help                  Show this message and exit.

As you can see, no global command are defined.
This is because the command are added to service and then depends on your code.

Try another simple command from the coworks directory::

    $ cws -p tests/example info
    microservice project1 defined in tests/example/example.py
    microservice project2 defined in tests/example/example.py

And complete description ::

    $ cws -p tests/example info --help


Predefined Coworks Commands
---------------------------

Let see some predefined commands before explaining how to create new ones.

The "info" command
^^^^^^^^^^^^^^^^^^

The first simple command is the microservice descriptor defined by the ``CwsDescriptor`` class.
It allows you to get simple informations on microservices defined in your project.

To add the command ``info`` to the service ``service`` defined in module ``module`` in the project directory ``src``::

    ... src/module.py ...

    service = ...
    CwsDescriptor(service)

Then you can call this command from the ``cws`` application::

	$ cws -p src -m module -s service info

**Notice**: The options ``-p (project_dir)`` , ``-m (module)`` and ``-s (service)`` are mandatory for launching
any command from the ``cws`` application.

**Notice**: There is also another client option ``-w (workspace)`` but its default value is ``dev`` and may be not
defined as optional.

Another way to add this command to any microservice is using the project configuration file described below.


The "run" command
^^^^^^^^^^^^^^^^^

A more complete command is the local runner defined by the ``CwsRunner`` class. It allows you to test your microservice
as a local service on your computer (as seen in the quickstart).

As defined previously, you can add the command by::

    ... src/module.py ...

    service = ...
    CwsRunner(service)

And then you can call this command from the ``cws`` application::

	$ cws -p src -m module -s service run


But this way, it is not easy to debug, so you can also run you microservice in a classical way of python application:

.. code-block:: python

    if __name__ == '__main__':
        app.execute('run', project_dir='.', workspace='dev')

**Notice**: In this case the ``service`` and ``module`` options are not needed and ``workspace`` is still optional.

You can add more options for testing such as changing the port or the stage::

	$ cws .. run --port 8001

or in python code:

.. code-block:: python

    if __name__ == '__main__':
        app.execute('run', project_dir='.', workspace='dev', port=8001)

To get the list of options::

	$ cws run --help

The "deploy" command
^^^^^^^^^^^^^^^^^^^^

Another important command is the ``deploy`` command defined for creating terraform files from templates.
This command may be used to deal with complex deployments, mainly for staging or respecting infrastucture constraints.

A more complete usage of this command is explained in the :ref:`tech_deployment` chapter.

Defining a new command
----------------------

To define a new command you have to define a sub class of the ``coworks.command.CwsCommand`` class::

    class CwsRunner(CwsCommand):
        ...

And give it a name when attached to the microservice::

    def __init__(self, app=None, name='run'):
        super().__init__(app, name=name)

You can add options as for ``click``::

    @property
    def options(self):
        return [
            *super().options,
            click.option('-h', '--host', default='127.0.0.1'),
            click.option('-p', '--port', default=8000, type=click.INT),
            click.option('--debug/--no-debug', default=False, help='Print debug logs to stderr.')
        ]

And at least, define the content execution code::

    def _execute(self, *, project_dir, module, service, workspace, host, port, debug, **options):
        ...

Project configuration file
--------------------------

This configuration file is a YAML file describing the microservices and the commands defined in the project.
Mainly this file is defined in two parts::

    version: ">0.3.3"
    services:
    commands:

The version key is used for compatibility. The services key introduce the ``services`` defined in the project,
and the ``commands`` one the commands.

Service part
^^^^^^^^^^^^

This part described the services defined in the project.

So if you pass no module and service option to the ``cws`` command it will apply this command to all services defined.
If you specify only the module, then the command will be applyed on all services of this module.

Here is an example :

.. code-block:: yaml

    services:
      - module: content_manager
        service: content_cms
      - module: configuration_manager
        services:
          - service: configuration_cms
          - service: authorization_cms


Command part
^^^^^^^^^^^^

This part described the commands and default options defined in the project.

Here is an example :

.. code-block:: yaml

    commands:
      run:
        class: coworks.cws.runner.CwsRunner
        port: 8000
      info:
        class: fpr.cws.FprInformant
      deploy:
        class: fpr.cws.deployer.FPRDeploy
        project_name: cms
        custom_layers: []
        binary_media_types: ["application/json", "text/plain"]
        profile_name: fpr-customer
        bucket: coworks-microservice
        services:
          - module: configuration_manager
            service: configuration_cms_ms
            workspaces:
              - workspace: prod
                common_layers: ["fpr-1", "storage-1"]
              - workspace: dev
                common_layers: ["fpr-dev", "storage-1"]
        workspaces:
          - workspace: prod
            common_layers: ["fpr-1"]
          - workspace: dev
            common_layers: ["fpr-dev"]

Testing
-------

Testing part is very important for CD/CI process.

PyTest Intergration
^^^^^^^^^^^^^^^^^^^

To create your tests for pytest, add this fixture in your ``conftest.py``::

	from coworks.pytest.fixture import local_server_factory

Then

.. code-block:: python

	def test_root(local_server_factory):
		local_server = local_server_factory(SimpleExampleMicroservice())
		response = local_server.make_call(requests.get, '/')
		assert response.status_code == 200

If you want to debug your test and stop on breakpoint, you need to increase request timeout:

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
