.. _installation:

Installation
============

Python Version
--------------

Currently ``CoWorks`` supports only AWS Lambda python3 versions (currently 3.7).

AWS Credentials
---------------

If you have previously configured your machine to run ``boto3`` (the AWS SDK for Python)
or the AWS CLI then you can skip this section.

Before you can deploy and test an application, be sure you have AWS credentials configured.
We recommand using, the share credentials file method `Shared Credentials <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html#shared-credentials-file>`_:

If you want more information on all the supported methods for configuring credentials, see
`boto3 <https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html>`_

Install
-------

Use a virtual environment to install CoWorks. We recommend using pipenv::

	$ mkdir project
	$ cd project
	$ pipenv install coworks
	$ pipenv shell

Check CoWorks is installed. Check it with::

	(project) $ cws --version

If you cannot found ``cws`` in your execution path, verify you activated the virtualenv for the project.

Within the activated environment, init the project with the following command ::

	(project) $ cws init

CoWorks is now ready for you.