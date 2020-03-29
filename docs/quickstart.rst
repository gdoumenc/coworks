.. _quickstart:

Quickstart
==========

This page gives a quick and partial introduction to CoWorks technical microservices.
Follow :doc:`installation` to set up a project and install CoWorks first.

A tech microservice is simply defined by a python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

Creation
--------

To realize you first techn microservice, create a file ``app.py`` with the following content:

.. code-block:: python

	from coworks import TechMicroService

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

	app = SimpleMicroService()

Test locally this microservice::

	(project) $ cws run
	Serving on http://127.0.0.1:8000

On another terminal enter::

	(project) $ curl http://127.0.0.1:8000
	Simple microservice ready.

Looks good..

Deployment with Chalice
-----------------------

Create the required dependencies for the lambda function::

	(project) $ pipenv lock -r > requirements.txt

Then enter the following command::

	(project) $ chalice deploy
	Creating deployment package.
	Creating IAM role: project-dev
	Creating lambda function: project-dev
	Creating Rest API
	Resources deployed:
		- Lambda ARN: arn:aws:lambda:eu-west-1:760589174259:function:project-dev
		- Rest API URL: https://9ssszma6mg.execute-api.eu-west-1.amazonaws.com/api/

That's it, your first microservice is online!

Execution
---------

Execute it::

	(project) $ curl https://9ssszma6mg.execute-api.eu-west-1.amazonaws.com/api/
	Simple microservice ready.

Deletion
--------

Now delete it ::

	(project) $ chalice delete

Finally, remove the project and its virtual environment ::

	(project) $ exit
	$ pipenv --rm
	$ cd ..
	$ rm -rf project

Commands
--------

To get all CoWorks commands and options::

	(project) $ cws --help
	Usage: cws [OPTIONS] COMMAND [ARGS]...

	Options:
	  --version           Show the version and exit.
	  --project-dir TEXT  The project directory path (absolute or
						  relative).Defaults to CWD
	  --help              Show this message and exit.

	Commands:
	  export
	  init
	  run

You can configure several files and entries in you project. for that use the ``module`` and ``app`` options of the
``run`` command::

	(project) $ cws run --help
	Usage: cws run [OPTIONS]

	Options:
	  -m, --module TEXT     Filename of your microservice python source file.
	  -a, --app TEXT        Coworks application in the source file.
	  -h, --host TEXT
	  -p, --port INTEGER
	  -s, --stage TEXT      Name of the Chalice stage for the local server to use.
	  --debug / --no-debug  Print debug logs to stderr.
	  --help                Show this message and exit.
