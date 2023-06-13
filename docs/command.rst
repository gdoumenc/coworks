.. _command:

Commands
========

As for Flask, CoWorks allows you to extend the ``cws`` application with ``click`` commands.
This powerfull extension is very usefull for complex deployment, testing or documentation.

As explained before, the microservice architecture needs to be completed by tools. The ``cws`` command line extends
the ``flask`` command for that purpose.

.. _cli:

CWS : Command Line Interface
----------------------------

``cws`` is an extension of the Flask command-line shell program that provides convenience and productivity
features to help user to :

* Get microservices informations,
* Export microservices to another formats,
* Deploy or update deployed microservices,
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
                                 [default to 'tech'].
      -c, --config-file TEXT     Configuration file path [relative from project
                                 dir].
      --config-file-suffix TEXT  Configuration file suffix.
      -S, --stage TEXT           The CoWorks stage (default dev).
      -e, --env-file FILE        Load environment variables from this file.
                                 python-dotenv must be installed.
      -A, --app IMPORT           The Flask application or factory function to
                                 load, in the form 'module:name'. Module can be a
                                 dotted import or file path. Name is not required
                                 if it is 'app', 'application', 'create_app', or
                                 'make_app', and can be 'name(args)' to pass
                                 arguments.
      --debug / --no-debug       Set debug mode.
      --help                     Show this message and exit.


    Commands:
      deploy    Deploy the CoWorks microservice on AWS Lambda.
      deployed  Retrieve the microservices deployed for this project.
      new       Creates a new CoWorks project.
      routes    Show the routes for the app.
      run       Run a development server.
      shell     Run a shell in the app context.
      zip       Zip all source files to create a Lambda file source.


As you can see, the default Flask commands as shell, routes or shell are predefined.
Some new commands as ``deploy`` have been defined.

**Note**: As the ``project_dir`` is not defined when you run the microservice without the ``run`` command,
for example in your IDE, you can define the environment variable ``INSTANCE_RELATIVE_PATH`` to be able to retrieve
the environment variable file. The value is a relative path from ``project_dir``.

At last the usefull variables:

* ``CWS_STAGE``: to determine which stage will be used (environment file).
* ``FLASK_DEBUG``: may be used same way as for Flask.

CoWorks Commands
-------------------

new
^^^

The ``new`` command creates an empty CoWorks project.

deploy
^^^^^^

The ``deploy`` command allows to deploy a ``TechMicroService`` on the AWS plateform.

This is done by creating terraform files from jinja template files. You can override those templates or add new files
if you needed to enhance the deployment process.

This command may be used to deal with complex deployments, mainly for staging or respecting infrastucture constraints
or processes.

How to change the deployment command?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is done by simply creating a new click command.
Find an example below::

    from coworks.cws.client import client

    # Get cws default deploy command
    deploy = client.commands['deploy']

    # Redefines new deploy command
    @pass_script_info
    @with_appcontext
    def new_deploy_callback(info, *args, **kwargs):
        app = info.load_app()
        kwargs['key'] = f"tech/{app.__module__}-{app.name}/archive.zip"
        kwargs['terraform_cloud'] = True
        return deploy.callback(*args, terraform_class=FprTerraformCloud, **kwargs)


    # Adds options
    deploy = client.commands['deploy']
    new_deploy = CwsCommand(deploy.name, callback=deploy_callback, params=deploy.params)
    click.option('--vpc', is_flag=True, default=True, help="Set lambda in VPC.")(new_deploy)
