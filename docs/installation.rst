.. _installation:

Installation
============

Python Version
--------------

Coworks supports only AWS Lambda python version >= 3.7.

Install Coworks
---------------

Use a virtual environment to install Coworks. We recommend using ``pipenv``::

	$ mkdir project
	$ cd project
	$ pipenv install coworks
	$ pipenv shell

You can then verify the installation by running::

	(project) $ cws --version

If you cannot find ``cws`` in your execution path, verify you activated the virtualenv for the project (this is achieved by running ``$ pipenv shell``).

Prior to use, please ensure that you also have the AWS CLI installed. You can check by running::

	$ aws --version

Coworks is now ready for use.

*Beware*: As ``awscli`` (and ``boto3``) often evolve, make sure you have a compatible versions in
your python virtual environment or dependencies conflicts may occur.

.. note:: Please see below sections on AWS and Terraform setup prior to deployment.

Create a project
----------------

To create a new project, go to the folder you want to set the project and enter::

	(project) $ cws new

If you want to try now without deploying, you may skip directly to :ref:`tech_quickstart`.

Other tools
-----------

AWS Credentials
***************

*If you have previously configured your machine to run boto3 (the AWS SDK for Python) or the
AWS CLI then you can skip this section.*

Before you can deploy an application, make sure you have an
`AWS account <https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account>`_
and configured the
`AWS credentials <https://docs.aws.amazon.com/sdk-for-php/v3/developer-guide/guide_credentials_profiles.html>`_.

Terraform
*********

*If you have previously installed terraform then you can skip this section.*

For deployment, for the command ``deploy`` we are using ``terraform``. We can use it locally or on
online cloud plateform ``terraform.io``.

Follow these `instructions <https://www.terraform.io/downloads.html>`_ to install terraform. Check installation with::

	(project) $ terraform --version

Terraform can also be used `online <https://www.terraform.io>`_.

You now have everything you need to create your first micro-service by following :ref:`tech_quickstart`
