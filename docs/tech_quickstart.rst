.. _tech_quickstart:

TechMicroService Quickstart
===========================

This page gives a quick and partial introduction to CoWorks Technical Microservices.
Follow :doc:`installation` to set up a project and install Coworks first.



A tech microservice is simply defined by a single python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

First try
---------

To create your first complete technical microservice, create a file ``first.py`` with the following content:

.. literalinclude:: ../samples/docs/quickstart.py

This first example defines a very simple microservice ``app`` with a simple ``GET`` entry ``/``
(see :ref:`routing` for more details on entry)

We have to add a new function ``token_authorizer`` to define an authorizer
(see :ref:`auth` for more details on authorizer).
For this simple test, the authorizer validates all token by returning ``True``.

This ``run`` command is defined by the ``Flask`` framework.

Test this microservice locally
(see `Flask <https://flask.palletsprojects.com/en/2.0.x/quickstart/#a-minimal-application>`_ for more details)::

	(project) $ FLASK_APP first:app cws run
	Serving on http://127.0.0.1:8000

On another terminal enter::

	(project) $ curl http://127.0.0.1:5000 -H Authorization=anyvalue
	Simple microservice ready.

Looks good...

Deploy the try
--------------

For that purpose, we add the ``deploy`` command to the microservice defined with the use of ``terraform``
(see `Terraform <https://www.terraform.io/>`_ for more details on Terraform).

For that purpose we have to define a project configuration file which defines this command::

.. literalinclude:: ../samples/docs/quickstart.cws.yml

And now we can upload the sources files to AWS S3 and apply terraform planifications::

	(project) $ FLASK_APP=first:app cws deploy
	Terraform apply (Create API routes)
    Terraform apply (Deploy API and Lambda for the dev stage)
    terraform output :
    classical_id = "c2ti48s5f0"
 	(project) $

As you can see, the command options are defined after the command itself :
``-p`` for the AWS credential profile,
``-b`` for the bucket name (see :ref:`command_definition` for more details on command options).

The ``-c`` option is not really needed but should be used each time you create an API to have expected messages.
It forces to accept API deletion ; this may happen on API modification so it is a good principle to use it only on API creation.
The ``-l`` option is for adding a layer to this lambda function.

In case you cannot use this layer, you can get the content file at
`CoWorks Layers <https://coworks-layer.s3-eu-west-1.amazonaws.com/coworks-0.5.0.zip/>`_ and create a layer with it.

Now we can try our first deployed microservice::

	(project) $ curl -H "Authorization:test" https://3avoth9jcg.execute-api.eu-west-1.amazonaws.com/dev
	Simple microservice ready.

Full project
------------

To complete we had a more complex microservice using the XRay context manager :

.. literalinclude:: ../samples/docs/complete.py

To avoid specifying all the options for the command, a project configuration file may be defined.
Let's define a very simple one:

.. literalinclude:: ../samples/docs/quickstart.cws.yml

A complete description of the syntax for the configuration project file is defined in.
Then the comand may simply called by:

.. code-block:: shell

	(project) $ cws deploy
	Uploading zip to S3
	Terraform apply (Update API)
	Terraform apply (Update lambda)
	Terraform apply (Update API routes)
	Terraform apply (Deploy API dev)
	terraform output : {'simplemicroservice': {'id': '3avoth9jcg'}}
	(project) $ curl -H "Authorization:test" https://3avoth9jcg.execute-api.eu-west-1.amazonaws.com/dev
	Stored value 0.
	(project) $ curl -H "Authorization:test" -H "Content-Type: application/json" -X POST -d '{"value":10}' https://3avoth9jcg.execute-api.eu-west-1.amazonaws.com/dev
	Value stored.
	(project) $ curl -H "Authorization:test" https://3avoth9jcg.execute-api.eu-west-1.amazonaws.com/dev
	Stored value 10.


Commands
--------

To view all CoWorks global options::

	(project) $ cws --help
