.. _installation:

Installation
============

Python Version
--------------

CoWorks supports only AWS Lambda python version >= 3.7 versions.

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

*Beware*: As ``awscli`` (even ``boto3``) evolves often, be sure you have a recent version of it if you have installed it in
your python virutal environment or dependencies conflicts may occur.