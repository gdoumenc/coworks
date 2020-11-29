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

First, we have to transfer the sources folder to AWS S3.

For that purpose, we add the ``zip`` command to the microservice

.. literalinclude:: ../tests/example/quickstart2.py

As you can see, a command can be renammed.

And now we can upload the sources folder to AWS S3::

	(project) $ cws -m first -s app upload -p fpr-customer -b coworks-microservice --debug --coworks-required_modules
        Upload sources...
        Successfully uploaded sources as coworks-microservice/first-simplemicroservice
        Upoad sources hash...
        Successfully uploaded sources hash as first-simplemicroservice.b64sha256
	(project) $

AS you can see also, the command options are defined after the command itself : ``-p`` for the AWS credential profile,
``-b`` for the bucket name and ``--debug`` for having trace
(see :ref:`command_definition` for more details on command options). The ``--coworks-required_modules`` option
uploads all python modules needed to execute the microservice without any specific layer.

Next, add the default ``CwsTerraformWriter`` extension to add the command to export terraform configuration files
from the microservice code:

.. literalinclude:: ../tests/example/quickstart3.py

Create the terraform files for deployment::

	(project) $ cws -m first -s app export -o app.tf

This will create an ``app.tf`` terraform file for managing all the ressources needed for this first simple microservice.

Enter the following command to initialize terraform::

	(project) $ terraform init
	Initializing the backend...
	...

And now apply the configuration (it will create the resources)::

	(project) $ terraform apply
	...
	Plan: 10 to add, 0 to change, 0 to destroy.

	Do you want to perform these actions?
	  Terraform will perform the actions described above.
	  Only 'yes' will be accepted to approve.

	  Enter a value: yes

	aws_api_gateway_rest_api.test: Creating...

Validate the creation by entering ``yes``.  Then, after all the resources have been created, you should get::

	Apply complete! Resources: 10 added, 0 changed, 0 destroyed.

	Outputs:

	test = {
	  "invoke-url" = "https://123456789123.execute-api.eu-west-1.amazonaws.com/dev"
	}

That's it, your first microservice is online! Let's try it out::

	(project) $ curl https://1aaaaa2bbb3c.execute-api.eu-west-1.amazonaws.com/dev -H "Authorization:token"
	Simple microservice ready.

Deletion
--------

Now, to destroy all the ressources created::

	(project) $ terraform destroy

Finally, to remove the project and its virtual environment::

	(project) $ exit
	$ pipenv --rm
	$ cd ..
	$ rm -rf project

Commands
--------

To view all Coworks commands and options::

	(project) $ cws --help
