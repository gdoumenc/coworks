.. _command:

CWS Command
===========

Coworks allows you to extends the ``cws`` application with commands. This powerfull extension is very usefull
for complex deployment or documentation.


.. _cli:

CWS Command Line Interface
--------------------------

cws
^^^

``cws`` is a command-line shell program that provides convenience and productivity
features to help user to :

 * Export information from microservice definition
 * Update deployed services

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


Coworks Command
---------------

Let see how predefined commands are defined before explaining how to create new ones.

The "run" command
^^^^^^^^^^^^^^^^^

The first simple command is the local runner defined by the ``CwsRunner``. It allows you to test your microservice
as a local service on your computer (as seen in the quickstart).

To add the command ``run`` to the service ``service`` defined in module ``module`` in the project directory ``src``::

    ... src/module.py ...

    service = ...
    CwsRunner(service)

Then you can call this command from the ``cws`` application::

	$ cws -p src -m module -s service run

**Notice**: The options ``-p (project_dir)`` , ``-m (module)`` and ``-s (service)`` are mandatory for launching
any command from the ``cws`` application.
There is also another client option ``-w (workspace)`` but its default value is ``dev``.

You can also run you microservice in a classical way of python application:

.. code-block:: python

    if __name__ == '__main__':
        app.execute('run', project_dir='.', module='app', workspace='dev')

**Notice**: In this case the ``service`` option is not needed and ``workspace`` is still optional.

You can add more options for testing such as changing the port or the stage::

	$ cws .. run --port 8001

or in python code:

.. code-block:: python

    if __name__ == '__main__':
        app.execute('run', project_dir='.', workspace='dev', module='quickstart', port=8001)

To get the list of options::

	$ cws run --help

The "deploy" command
^^^^^^^^^^^^^^^^^^^^

Another important command is the ``export`` command defined for creating terraform files from templates.
This command may be used to deal with complex deployments, mainly for staging or infrastucture constraints.

Thus use of this command is explain in :ref:`tech_deployment` chapter.

Defining a new command
^^^^^^^^^^^^^^^^^^^^^^

To define a new command you have to define a sub class of ``coworks.command.CwsCommand``::

    class CwsRunner(CwsCommand):
        ...

And give it a name::

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

And at least, the content execution code::

    def _execute(self, *, project_dir, workspace, host, port, debug, **options):

cws.project.yml file
^^^^^^^^^^^^^^^^^^^^

This configuration file, defined in the project directory can facilitate the launch of commands by
providing default commands arguments values.

PyTest
^^^^^^

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
