.. _installation:

Installation
============

Python Version
--------------

CoWorks supports only AWS Lambda python version >= 3.7 versions.

Install CoWorks
---------------

Use a virtual environment to install CoWorks. We recommend using ``pipenv``::

	$ mkdir project
	$ cd project
	$ pipenv install coworks
	$ pipenv shell

Check CoWorks is installed. Check it with::

	(project) $ cws --version

If you cannot find ``cws`` in your execution path, verify you activated the virtualenv for the project.

CoWorks is now ready for you.

*Beware*: As ``awscli`` (even ``boto3``) often evolves, make sure you have a compatible version of it in
your python virtual environment or dependencies conflicts may occur.

If you want to try now without deploying, you skip to :ref:`tech_quickstart`.

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

For deployment, ``chalice`` provide a very simple and powerfull deployment command (``deploy``) but we recommand using
``terraform`` for your projects.

Follow these `instructions <https://www.terraform.io/downloads.html>`_ to install terraform. Check installation with::

	(project) $ terraform --version

Terraform can also be used `online <https://www.terraform.io>`_.

SCons
*****

In order to reduce deployment duration, we use AWS Lambda
`Layer <https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html>`_.
Thanks to layers, we can use libraries
in our miscroserrvice without having to include them in the deployment package. We use
`SCons <https://scons.org/>`_ to create layers.

*Note*: To keep the `coworks` library as smaller as possible the `scons` package is not embeded as you can
use any other tools for deployment.

To install SCons::

	(project) $ pipenv install SCons

*Beware*: `scons` must not be installed with a system package tool such as `apt` as the python library is needed in our
deployment process.

Check installation with::

	(project) $ scons --version

You now have everything you need to create your first micro-service :ref:`tech_quickstart`
