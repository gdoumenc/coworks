.. _installation:

Installation
============

Python Version
--------------

CoWorks supports only AWS Lambda python version >= 3.7.

Install Coworks
---------------

Use a virtual environment to install CoWorks. We recommend using ``pipenv``::

	$ mkdir project
	$ cd project
	$ pipenv install coworks
	$ pipenv shell

You can then verify the installation by running::

	(project) $ cws --version


CoWorks is now ready for use.

Create a project
----------------

To create a new project, enter::

	(project) $ cws new

You now have everything you need to create your first micro-service by following :ref:`tech_quickstart`

Other tools
-----------

.. note:: Please see below sections on AWS and Terraform setup prior to deployment.

Prior to use, please ensure that you also have the AWS CLI and Terrraform binary installed. You can check by running::

	$ aws --version
	$ terraform --version


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
