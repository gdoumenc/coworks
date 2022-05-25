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

``cws`` is an extension of the Flask command-line shell program that provides convenience and productivity
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
      --version                  Show the version and exit.
      -p, --project-dir TEXT     The project directory path (absolute or relative)
                                 [default to '.'].
      -c, --config-file TEXT     Configuration file path [relative from project
                                 dir].
      --config-file-suffix TEXT  Configuration file suffix.
      --help                     Show this message and exit.

    Commands:
      deploy    Deploy the CoWorks microservice on AWS Lambda.
      deployed  Retrieve the microservices deployed for this project.
      new       Creates a new CoWorks project.
      routes    Show the routes for the app.
      run       Run a development server.
      shell     Run a shell in the app context.
      zip       Zip all source files to create a Lambda file source.


As you can see, the default Falsk command as shell, routes or shell are predefined.
A new command ``deploy`` has been defined.

The options ``-p (project_dir)`` is mandatory if the ``cws`` command is not issued in the source folder.

**Note**: As the ``project_dir`` is not defined when you run the microservice without the ``run`` command,
for example in your IDE, you can define the environment variable ``INSTANCE_RELATIVE_PATH`` to be able to retrieve
the environment variable file. The value is a relative path from ``project_dir``.

At last the usefull variables ``FLASK_ENV`` and ``FLASK_DEBUG`` may be used same way as for Flask.

Example of a simple command from the coworks directory::

    $ FLASK_APP=app:app cws -p samples/headless info
    microservice project1 defined in tests/example/example.py
    microservice project2 defined in tests/example/example.py

And to get complete command description::

    $ cws CMD --help


CoWorks Commands
-------------------

The "deploy" command
^^^^^^^^^^^^^^^^^^^^

The ``deploy`` command is defined to deploy the microservice on the AWS plateform.

This is done by creating terraform files from jinja template files. You can override those templates or add new files
if you needed to enhance the deployment process.

This command may be used to deal with complex deployments, mainly for staging or respecting infrastucture constraints
or processes.

