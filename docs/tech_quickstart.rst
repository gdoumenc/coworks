.. _tech_quickstart:

TechMS Quickstart
=================

This page gives a quick and partial introduction to CoWorks technical microservices.
Follow :doc:`installation` to set up a project and install CoWorks first.

A tech microservice is simply defined by a python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

First try
---------

To create your first complete technical microservice, create a file ``app.py`` with the following content:

.. literalinclude:: ../tests/example/quickstart1.py

Test locally this microservice::

	(project) $ cws run
	Serving on http://127.0.0.1:8000


On another terminal enter::

	(project) $ curl http://127.0.0.1:8000
	Simple microservice ready.

Looks good...

Convert the try
---------------

First we will create the layer with the ``scons`` tool. This layer will contain all the needed python modules
for a simple execution.

For that purpose, create a file ``SConstruct`` with following content:

.. literalinclude:: ../tests/example/SConstruct

Then do the following command::

	(project) $ scons
	scons: Reading SConscript files ...
	scons: done reading SConscript files.
	scons: Building targets ...
	generate_zip_file(["layer.zip"], [])
	scons: done building targets.

A ``layer.zip`` file is then available.

Next, add the default ``TerraformWriter`` to export terraform configuration file from the microservice code:

.. literalinclude:: ../tests/example/quickstart2.py

Create the terraform files for deployment::

	(project) $ cws export -o app.tf

This will create an ``app.tf`` terraform file for managing all the ressources needed for this first simple microservice.


Enter the following command to initialize terraform::

	(project) $ terraform init
	Initializing the backend...

	Initializing provider plugins...
	- Checking for available provider plugins...
	- Downloading plugin for provider "aws" (hashicorp/aws) 2.62.0...
	- Downloading plugin for provider "archive" (hashicorp/archive) 1.3.0...
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

Validate the creation by entering ``yes``. Then after the creation of all resources::

	Apply complete! Resources: 10 added, 0 changed, 0 destroyed.

	Outputs:

	test = {
	  "invoke-url" = "https://123456789123.execute-api.eu-west-1.amazonaws.com/dev"
	}

That's it, your first microservice is online! Let try::

	(project) $ curl https://1aaaaa2bbb3c.execute-api.eu-west-1.amazonaws.com/dev -H "Authorization:token"
	Simple microservice ready.

Deletion
--------

Now destroy all created  ressources::

	(project) $ terraform destroy

Finally, remove the project and its virtual environment::

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
	  --version               Show the version and exit.
	  -p, --project-dir TEXT  The project directory path (absolute or relative).
							  Defaults to CWD

	  --help                  Show this message and exit.

	Commands:
	  export  Export microservice in other description languages.
	  info    Information on a microservice.
	  run     Run local server.
	  update  Update biz microservice.
