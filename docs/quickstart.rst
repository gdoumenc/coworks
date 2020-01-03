.. _quickstart:

Quickstart
==========

This page gives a quick introduction to CoWorks.
Follow :doc:`installation` to set up a project and install CoWorks first.

A microservice is simply defined by a python class which looks like this:

.. code-block:: python

	class SimpleExampleMicroservice(TechMicroService):

		def get(self):
			return f"Hello world.\n"

Creation
--------

To realize you first microservice, create a file ``app.py`` with the following content:

.. code-block:: python

	from coworks import TechMicroService

	class SimpleExampleMicroservice(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

	app = SimpleExampleMicroservice()

Test locally this microservice::

	(project) $ cws local
	Serving on http://127.0.0.1:8000

On another terminal enter::

	(project) $ curl http://127.0.0.1:8000
	Simple microservice ready.

Looks good..

Deployment
----------

Create the required dependencies for the lambda function::

	(project) $ pipenv lock -r > requirements.txt

Then enter the following command::

	(project) $ cws deploy
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

	(project) $ cws delete

Finally, remove the project and its virtual environment ::

	(project) $ exit
	$ pipenv --rm
	$ cd ..
	$ rm -rf project

