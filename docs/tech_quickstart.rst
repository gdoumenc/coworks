.. _tech_quickstart:

TechMS Quickstart
=================

This page gives a quick and partial introduction to Coworks technical microservices.
Follow :doc:`installation` to set up a project and install Coworks first.

A tech microservice is simply defined by a single python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

First try
---------

To create your first complete technical microservice, create a file ``first.py`` with the following content:

.. literalinclude:: ../tests/example/quickstart1.py

This first example defines a very simple microservice ``app`` with a simple ``GET`` entry ``/``
(see :ref:`routing` for more details on entry)
and adds it a local ``run`` command (see :ref:`command` for more details on command).

This ``run`` command is defined by the ``CwsRunner`` extension added to the microservice.

Test this microservice locally::

	(project) $ cws -m first -s app run
	Serving on http://127.0.0.1:8000

The ``-m`` option defines the python module and ``-s`` the variable in this module implementing the microservice
(see :ref:`cli` for more details on cws client)

On another terminal enter::

	(project) $ curl http://127.0.0.1:8000
	Simple microservice ready.

Looks good...

Deploy the try
--------------

For that purpose, we add the ``deploy`` command to the microservice defined with the use of ``terraform``
(see `Terraform <https://www.terraform.io/>`_ for more details on Terraform).

.. literalinclude:: ../tests/example/quickstart2.py

We have to add a new function ``auth`` to define an authorizer (see :ref:`auth` for more details on authorizer).
For this simple test, the authorizer validates all the routes by returning ``True``.

As you can see we have added the command ``CwsTerraformDeployer`` to this microservice.
This command is a combinaison of two other commmands ``CwsZipArchiver`` and ``CwsTemplateWriter``::

    class CwsTerraformDeployer(CwsCommand):

        def __init__(self, app=None, name='deploy'):
            self.zip_cmd = CwsZipArchiver(app)
            CwsTemplateWriter(app)
            super().__init__(app, name=name)


The ``CwsZipArchiver`` is a command to create a zip source file and uploading this zip file
to AWS S3.

The ``CwsTemplateWriter`` is a command to generate files from Jinja2 templates
(see `Jinja2 <https://jinja.palletsprojects.com/>`_ for more details on Jinja2). In this command the files will be
terraform files.

And now we can upload the sources files to AWS S3 and apply terraform planifications::

	(project) $ cws -m first -s app deploy -p fpr-customer -b coworks-microservice -c -l arn:aws:lambda:eu-west-1:935392763270:layer:coworks-0_3_5
        Are you sure you want to (re)create the API [yN]?:y
        Uploading zip to S3
        Terraform apply (Create API)
        Terraform apply (Create lambda)
        Terraform apply (Update API routes)
        Terraform apply (Deploy API dev)
        terraform output : {'first-simplemicroservice': {'id': '3avoth9jcg'}}
	(project) $

As you can see, the command options are defined after the command itself :
``-p`` for the AWS credential profile,
``-b`` for the bucket name (see :ref:`command_definition` for more details on command options).

The ``-c`` option is not really needed but should be used each time you create an API to have expected messages.
It forces to accept API deletion ; this may happen on API modification so it is a good principle to use it only on API creation.
The ``-l`` option is for adding a layer to this lambda function.

In case you cannot use this layer, you can get the content file at
`CoWorks Layers <https://coworks-layer.s3-eu-west-1.amazonaws.com/coworks-0.3.3.zip/>`_ and create a layer with it.

Now we can try our first deployed microservice::

	(project) $ curl -H "Authorization:test" https://3avoth9jcg.execute-api.eu-west-1.amazonaws.com/dev
	Simple microservice ready.

Full project
------------

To complete we had a more complex microservice using the XRay context manager :

.. literalinclude:: ../tests/example/first.py

To avoid specifying all the options for the command, a project configuration file may be defined.
Let's define a very simple one:

.. literalinclude:: ../tests/example/quickstart.cws.yml

A complete description of the syntax for the configuration project file is defined in.
Then the comand may simply called by:

.. code-block:: python

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
