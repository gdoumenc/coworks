.. _command:

Commands
========

Coworks allows you to extend the ``cws`` application with commands. This powerfull extension is very usefull
for complex deployment, testing or documentation.

As explained before, the microservice architecture needs to be completed by tools. The ``cws`` command line is
the interface for that purpose.

.. _cli:

CWS : Command Line Interface
----------------------------

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

	$ cws --help
    Usage: cws [OPTIONS] COMMAND [ARGS]...

    Options:
      --version               Show the version and exit.
      -p, --project-dir TEXT  The project directory path (absolute or relative)
                              [default to '.'].

      -c, --config-file TEXT  Configuration file path [path from project dir].
      -m, --module TEXT       Filename of your microservice python source file.
      -s, --service TEXT      Microservice variable name in the source file.
      -w, --workspace TEXT    Application stage [default to 'dev'].
      --help                  Show this message and exit.

As you can see, no global command are defined.
This is because the command are added to service and then depends on your code.

The options ``-p (project_dir)`` is mandatory if the ``cws`` command is not issued in the source folder.

The options ``-m (module)`` and ``-s (service)`` are mandatory for launching
any command from the ``cws`` if a configuration project is not defined in the source folder.

At last the optional option ``-w (workspace)`` which default value is ``dev`` defines execution stage.

Example of a simple command from the coworks directory::

    $ cws -p samples/headless info
    microservice project1 defined in tests/example/example.py
    microservice project2 defined in tests/example/example.py

And to get complete command description::

    $ cws CMD --help


Predefined Commands
-------------------

Let see some predefined commands before explaining how to create new ones.

The "inspect" command
^^^^^^^^^^^^^^^^^^^^^

The first simple command is the microservice descriptor defined by the ``CwsInspector`` class.
It allows you to get simple informations on microservices defined in your project.

To add the command ``inspect`` to the service ``service`` defined in module ``module`` in the project directory ``src``::

    ... src/module.py ...

    service = ...
    CwsDescriptor(service)

Then you can call this command from the ``cws`` application::

	$ cws -p src -m module -s service info

Another way to add this command to any microservice is using the project configuration file described below.


The "run" command
^^^^^^^^^^^^^^^^^

A more complete command is the local runner defined by the ``CwsRunner`` command class.
It allows you to test your microservice as a local service on your computer (as seen in the quickstart).

As defined previously, you can add the command by::

    ... src/module.py ...

    service = ...
    CwsRunner(service)

And then you can call this command from the ``cws`` application::

	$ cws -p src -m module -s service run


But this way, it is not easy to debug in your IDE, so you can also run you microservice
in a classical way of python application:

.. code-block:: python

    if __name__ == '__main__':
        app.execute('run', project_dir='.', workspace='dev')

**Notice**: In this case the ``service`` option is not needed,
the ``module`` option is used only for trace and the ``workspace`` option is still optional.

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

.. _command_definition:

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

