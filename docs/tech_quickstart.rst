.. _tech_quickstart:

Tech Quickstart
===============

This page gives a quick and partial introduction to CoWorks Technical Microservices.
Follow :doc:`installation` to install CoWorks and set up a new project.

CoWorks Technical Microservices are `atomic microservices`, meaning that they are single `atomic` components
(i.e: singular blobs of code with a few inputs and outputs).

A tech microservice is simply defined by a single python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

Start
-----

To create your first complete technical microservice, create a file ``hello.py`` in the ``tech`` folder
with the following content:

.. literalinclude:: ../samples/docs/tech/hello.py

This first example defines the very classical ``hello`` microservice ``app`` with a simple ``GET`` entry ``/``
(see :ref:`routing` for more details on entry)

We set the attribute ``no_auth`` to ``True`` to allow access without authorization.
This effectively disables the token authorizer.
For security reason the default value is ``False`` (see :ref:`auth` for more details on authorizer).

We now can launch the ``run`` command defined by the ``Flask`` framework. So to test this microservice locally
(see `Flask <https://flask.palletsprojects.com/en/2.0.x/quickstart/#a-minimal-application>`_ for more details)::

    (project) $ cws --app hello run
     * Stage: dev
     * Serving Flask app 'hello'
     * Debug mode: off
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
     * Running on http://127.0.0.1:5000
    Press CTRL+C to quit

To test this example, open another terminal window and enter::

	(project) $ curl http://127.0.0.1:5000/
	Hello world.

If you remove the argument ``no_auth=True`` from our ``@entry`` decorator, you should instead receive a 403 response.

First
-----

To add more elements, complete your first try with the following content:

.. literalinclude:: ../samples/docs/tech/first.py

We have added a dedicated function ``token_authorizer`` to define an authorizer
(see :ref:`auth` for more details on authorizer).
For this simple try, the authorizer validates the request only if a token is defined on header with the ``token``
as value.

Then we have defined two entries on same path : ``GET`` and ``POST`` on root path.
These enable reading and writing of our attribute ``value``.

To test this example, open another terminal window and enter::

	(project) $ curl -I http://127.0.0.1:5000/
	HTTP/1.0 401 UNAUTHORIZED
	...

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/
	Stored value 0.

	(project) $ curl -X POST -d '{"value":20}' -H "Content-Type: application/json" -H "Authorization:token" http://127.0.0.1:5000/
	Value stored (20).

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/
	Stored value 20.

*Beware* : the ``value`` is stored in memory just for this example, if the lambda is redeployed or another lambda instance
is used the value stored is lost.

Complete
--------

We can create and test a more complete case by leveraging blueprints and adding middlewares.
We will also use `StringIO <https://docs.python.org/3/library/io.html#text-i-o>`_ to write our output to a string buffer.

For more information on how CoWorks uses blueprints, see `TechMS Blueprints <https://coworks.readthedocs.io/en/master/tech.html#blueprints>`_.
For more information on how CoWorks uses WSGI middlewares, see `Middlewares <https://coworks.readthedocs.io/en/master/middleware.html>`_.

First, ensure that `aws_xray_sdk` is installed in your python environment::

	$ pip install aws-xray-sdk

Then, enter the following content:

.. literalinclude:: ../samples/docs/tech/complete.py

*Note* : `aws_xray_sdk` must be installed in your python environment or you will get an ``ImportError``.
If you receive this error, follow the step above to install.

Install a dotenv file (``.env``) with the token value defined in it.

The ``Admin`` blueprint `adds several routes <https://coworks.readthedocs.io/en/master/tech.html#admin>`_ but
for the purposes of this example we're interested in the root one (``/admin`` as prefixed):

		This endpoint gives documentation and all the routes of the microservice with the signature extracted from its associated function.

We have also a WSGI middleware ``ProfilerMiddleware`` to profile the last request::

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/profile
    --------------------------------------------------------------------------------
    PATH: '/profile'
             441 function calls (436 primitive calls) in 0.001 seconds

       Ordered by: internal time, call count

       ncalls  tottime  percall  cumtime  percall filename:lineno(function)
            1    0.000    0.000    0.000    0.000 {method 'getvalue' of '_io.StringIO' objects}
            1    0.000    0.000    0.000    0.000 /home/gdo/.local/share/virtualenvs/samples-G9jKBMQA/lib/python3.10/site-packages/werkzeug/routing/map.py:246(bind_to_environ)
           11    0.000    0.000    0.000    0.000 /home/gdo/.local/share/virtualenvs/samples-G9jKBMQA/lib/python3.10/site-packages/werkzeug/local.py:308(__get__)
        ...

And at last we have a CoWorks middleware to add `XRay traces <https://docs.aws.amazon.com/xray/latest/devguide/aws-xray.html>`_ (available only for deployed microservices).

Deploy
------

And now we can upload the sources files to AWS S3 and apply predefined terraform planifications (options may be defined
in project file to avoid given then on command line see :ref:`configuration` )::

	(project) $ cws --app first deploy --bucket XXX --profile-name YYY --layers arn:aws:lambda:eu-west-1:935392763270:layer:coworks-ZZZ
	Terraform apply (Create API routes)
	Terraform apply (Deploy API and Lambda for the dev stage)
	terraform output :
	classical_id = "xxxxxxxx"
	(project) $

**Notice**: To get the available coworks layer versions, just call this public microservice
(source code available in ``samples/layers``)::

	curl -H 'Accept:application/json' https://2kb9hn4bs4.execute-api.eu-west-1.amazonaws.com/v1

Now we can test our first deployed microservice::

	(project) $ curl -H "Authorization:token" https://xxxxxxxx.execute-api.eu-west-1.amazonaws.com/dev
	Stored value 0.

**Notice**: The deploy parameters can be defined once in the project configuration file (``project.cws.yml``)

