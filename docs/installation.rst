.. _installation:

Installation
============

Python Version
--------------

CoWorks supports only AWS Lambda python3 versions (currently 3.7).

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