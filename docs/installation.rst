.. _installation:

Installation
============

Python Version
--------------

CoWorks supports only AWS Lambda python version >= 3.7 versions.

Install CoWorks
---------------

Use a virtual environment to install CoWorks. We recommend using pipenv::

	$ mkdir project
	$ cd project
	$ pipenv install coworks
	$ pipenv shell

Check CoWorks is installed. Check it with::

	(project) $ cws --version

If you cannot found ``cws`` in your execution path, verify you activated the virtualenv for the project.

CoWorks is now ready for you.

*Beware*: As ``awscli`` (even ``boto3``) evolves often, be sure you have a compatible version of it in
your python virtual environment or dependencies conflicts may occur.

Other tools
-----------

AWS Credentials
***************

*If you have previously configured your machine to run boto3 (the AWS SDK for Python) or the
AWS CLI then you can skip this section.*

Before you can deploy an application, be sure you have an
`AWS account <https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account>`_
and configured the
`AWS credentials <https://docs.aws.amazon.com/sdk-for-php/v3/developer-guide/guide_credentials_profiles.html>`_

Terraform
*********

For deployment ``chalice`` provide a very simple and powerfull deployment command (``deploy``) but we recommand using
``terraform`` for your projects.

Follow these `instructions <https://www.terraform.io/downloads.html>`_ to install terraform. Check installation with::

	(project) $ terraform --version

Terraform can be also used `online <https://www.terraform.io>`_.

SCons
*****

To reduce deployment duration, we use AWS Lambda
`Layer <https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html>`_.
With layers, we can use libraries
in our miscroserrvice without needing to include them in the deployment package. To create the layer,
we use `SCons <https://scons.org/>`_.

To install SCons ::

	(project) $ pipenv install SCons

Check installation with::

	(project) $ scons --version
	SCons by Steven Knight et al.:
		script: v3.1.2.bee7caf9defd6e108fc2998a2520ddb36a967691, 2019-12-17 02:07:09, by bdeegan on octodog
		engine: v3.1.2.bee7caf9defd6e108fc2998a2520ddb36a967691, 2019-12-17 02:07:09, by bdeegan on octodog
		engine path: ['/home/studiogdo/.pyenv/versions/3.7.2/lib/python3.7/site-packages/scons/SCons']
	Copyright (c) 2001 - 2019 The SCons Foundation

Now you have everything to create your first microservice :ref:`tech_quickstart`
