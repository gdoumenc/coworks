.. _tech_quickstart:

TechMS Quickstart
=================

This page gives a quick and partial introduction to Coworks Technical Microservices.
Follow :doc:`installation` to install Coworks and set up a new project.

Coworks Technical Microservices are ``atomic microservices``, meaning that they are single ``atomic`` components (i.e: singular blobs of code with a few inputs and outputs).

A tech microservice is simply defined by a single python class which looks like this:

.. code-block:: python

	class SimpleMicroService(TechMicroService):

		def get(self):
			return f"Simple microservice ready.\n"

Start
-----

To create your first complete technical microservice, create a file ``simple.py`` with the following content:

.. literalinclude:: ../samples/docs/simple.py

This first example defines a very simple microservice ``app`` with a simple ``GET`` entry ``/``
(see :ref:`routing` for more details on entry)

We set the attribute ``no_auth`` to ``True`` to allow any token as valid. This effectively disables the token authorizer.
For security reason the default value is ``False`` (see :ref:`auth` for more details on authorizer).

We now can launch the ``run`` command defined by the ``Flask`` framework. So to test this microservice locally
(see `Flask <https://flask.palletsprojects.com/en/2.0.x/quickstart/#a-minimal-application>`_ for more details)::

	(project) $ FLASK_APP=simple cws run
	* Serving Flask app 'simple:app' (lazy loading)
	* Environment: production
	  WARNING: This is a development server. Do not use it in a production deployment.
	  Use a production WSGI server instead.
	* Debug mode: off
	* Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)


On another terminal enter::

	(project) $ curl -H "Authorization:any" http://127.0.0.1:5000/
	Hello world.

If you remove the argument ``no_auth=True`` from our ``@entry`` decorator, you should instead receive a 403 response.

More
----

To add more elements, complete the try with the following content:

.. literalinclude:: ../samples/docs/first.py

We have added a dedicated function ``token_authorizer`` to define an authorizer
(see :ref:`auth` for more details on authorizer).
For this simple try, the authorizer validates the request only if a token is defined on header withe ``token``
as value.

Then have defined two entries on same path : ``GET`` and ``POST`` on root path.

On the another terminal enter::

	(project) $ curl -I http://127.0.0.1:5000/
	HTTP/1.0 401 UNAUTHORIZED
	...

	(project) $ curl -I -H "Authorization:any" http://127.0.0.1:5000/
	HTTP/1.0 403 FORBIDDEN
	...

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/
	Stored value 0.

	(project) $ curl -X POST -d '{"value":20}' -H "Content-Type: application/json" -H "Authorization:token" http://127.0.0.1:5000/
	Value stored (20).

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/
	Stored value 20.

*Beware* : the value is stored in memory just for this example, if the lambda is redeployed or another lambda instance
is used the value is lost.

Complete
--------

At last to have a complete case, enter the following content:

.. literalinclude:: ../samples/docs/complete.py

*Note* : `aws_xray_sdk` must be installed in your python environment or you will get an ``ImportError``.

We have added some blueprints and middlewares to add routes and functionalities.

The ``Admin`` blueprint adds several routes but mainly the ``route`` one::

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/admin/route?pretty=1
	{
        "/": {
            "POST": {
                "doc": "",
                "signature": "(value=None)"
            }
        },
        "/admin/context": {
            "GET": {
                "doc": "Returns the calling context.",
                "signature": "()"
            }
        },
        "/admin/env": {
            "GET": {
                "doc": "Returns the stage environment.",
                "signature": "()"
            }
        },
        "/admin/event": {
            "GET": {
                "doc": "Returns the calling context.",
                "signature": "()"
            }
        },
        "/admin/route": {
            "GET": {
                "doc": "Returns the list of entrypoints with signature.",
                "signature": "(pretty=False)"
            }
        },
        "/profile": {
            "GET": {
                "doc": "",
                "signature": "()"
            }
        }
    }

We have also a WSGI middleware ``ProfilerMiddleware`` to profile the last request::

	(project) $ curl -H "Authorization:token" http://127.0.0.1:5000/profile
	--------------------------------------------------------------------------------
	PATH: '/admin/route'
			14689 function calls (14287 primitive calls) in 0.012 seconds

		Ordered by: internal time, call count

		ncalls  tottime  percall  cumtime  percall filename:lineno(function)
			42    0.001    0.000    0.001    0.000 {built-in method builtins.compile}
			728    0.001    0.000    0.002    0.000 /home/gdo/.pyenv/versions/3.8.11/lib/python3.8/ast.py:222(iter_child_nodes)
			14    0.001    0.000    0.006    0.000 /home/gdo/.local/share/virtualenvs/coworks-otSHAmdg/lib/python3.8/site-packages/werkzeug/routing.py:968(_compile_builder)
	...

And at last we have a Coworks middleware to add XRay traces (available only in case of deployed microservice).

Deploy
------

And now we can upload the sources files to AWS S3 and apply predefined terraform planifications (options may be defined
in project file to avoid given then on command line see :ref:`configuration` )::

	(project) $ FLASK_APP=simple:app cws deploy
	Terraform apply (Create API routes)
	Terraform apply (Deploy API and Lambda for the dev stage)
	terraform output :
	classical_id = "xxxxxxxx"
	(project) $

Now we can try our first deployed microservice::

	(project) $ curl -H "Authorization:test" https://xxxxxxxx.execute-api.eu-west-1.amazonaws.com/dev
	Stored value 0.
