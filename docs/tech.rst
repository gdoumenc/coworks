.. _tech:

TechMS
======

TechMicroservices are the 'atoms' of the Coworks microservices framework. They represent the building blocks
for other more complex 'compound' microservices.

Defining Tech Microservices
---------------------------

The microservice class can be defined as a class inheriting from ``TechMicroService``:

.. code-block:: python

  class SimpleMicroService(TechMicroService):
    pass

.. _routing:

Routing
-------

Routes are defined by decorated functions in the microservice class.

The decorator is::

    @entry

The function names must follow the syntax below::

	<request_method>_<associated_route>

The request method is then defined for the associated route.
Composed routes are defined with the ``_`` separator.

For example, ``get_content`` would define the request method ``GET`` for route ``/content``.
Please see more examples in below section:

Examples
^^^^^^^^

The following function defines the GET method for the root path of the microservice:

.. code-block:: python

    @entry
    def get(self):
        return "root"

The following function defines the GET method for the route ``/service/test``:

.. code-block:: python

    @entry
    def get_service_test(self):
		return "service test"

The following function defines the PUT method for the root path:

.. code-block:: python

    @entry
    def put(self):
		return "put"

Entrypoint Parameters
---------------------

URI Parameters
^^^^^^^^^^^^^^

You can define entrypoint function arguments as part of the URI:

.. code-block:: python

	@entry
	def get_content(self, index):
		return f"get content {index}"

This defines a route which first part is the fixed string ``content`` and the second part is the ``index`` value.
We denote the route like this::

	/content/{index}

You can have several positional parameters (ordered from the URL path):

.. code-block:: python

	@entry
	def get_content(self, bucket, key1, key2, key3):
		return f"get content of {bucket} with key {key1/key2/key3}"

which defines the route ``/content/{bucket}/{key1}/{key2}/{key3}``.

*Note*: In this case, the keys parameters must not have the ``/`` character.

You can also construct more complex routes from different parameters:

.. code-block:: python

	@entry
	def get_content(self):
		return "get content"

	@entry
	def get_content_(self, value):
		return f"get content with {value}"

	@entry
	def get_content__(self, value, other):
		return f"get content with {value} and {other}"

This defines the respective following routes::

	/content
	/content/{value}
	/content/{value}/{other}

This is useful for offering a CRUD microservice:

.. code-block:: python

	@entry
	def get(self):
		return "the list of instances of a model"

	@entry
	def get_(self, id):
		return f"the instance with id {id}"

	@entry
	def post(self, data):
		return f"creates a new instance with {data}"

	@entry
	def put(self, id, data):
		return f"modifies an instance identified by {id} with {data}"

Typed parameters
^^^^^^^^^^^^^^^^

You can specify the type of your URI parameters or data query in order to use native built-in types (other than the default of string).

.. code-block:: python

	@entry
  # id of type int
	def get(self, id:int):
		return f"the type of id is {type(id)}"

	@entry
  # id of type int with default value None
	def get_(self, id:int = None):
		return f"the type of id is {type(id)}"


Query or body parameters
^^^^^^^^^^^^^^^^^^^^^^^^

You can define default parameters to your entry point function.
In that case the value of those default parameters are defined by query parameters or JSON content.

.. code-block:: python

	@entry
	def get_content(self, id=None, name=""):
		return f"the instance with id {id} and/or name {name}"

Where the ``id`` parameter can be defined by the query parameter::

	/content?id=32&name=test

Or in python code using the ``requests`` module::

	requests.get("/content", params={"id": 32, "name": "test"})

or by a JSON structure::

	request.get("/content", json={"id": 32, "name": "test"})

A list parameter can be defined by a multi value parameter::

	/content?id=32&name=test&name=other

Which is equivalent to the JSON call::

	request.get("/content", json={"id": 32, "name": ["test", "other"]})

*Beware*: With `API gateway` you can only use query parameters for a ``GET`` method. Attempting
to send data in the request body for a ``GET`` request will raise an error in execution.

You can also use the ``**`` notation to get any values::

	@entry
	def get_content(self, **kwargs):
		return f"here are all the parameters: {kwargs}"

For more information on how to use keyword arguments in Python, see `this useful article <https://www.programiz.com/python-programming/args-and-kwargs>`_

**Note**: The current implementation doesn't take into account the typing of the entry point function parameters
(forcasted in a future release).
So all query parameters are from type ``string``. If you want to pass typed or structured values, use the JSON mode.

Entrypoints
^^^^^^^^^^^

The entries define routes with the following format :

* For an app entry : {function_name}
* For an blueprint entry : {blueprint_name}.{function_name}

For example ::

    url_for('get') # app root entry
    url_for('manager.get_dashboard') # get_dashborad entry for the manager blueprint

Disable authorizer for an entry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If needed you can disable the token authorizer on an entry:

.. code-block:: python

	from coworks import TechMicroService
	from coworks import entry

	class SimpleExampleMicroservice(TechMicroService):

		@entry(no_auth=True)
		def get(self):
			return "Entry without authorizer."


Content type
^^^^^^^^^^^^

By default all entries are defined as ``application/json`` content-type. You can change this default value for an entry,
so all simple returned responses will have this content type value, thus avoiding to add the specific header value.

.. code-block:: python

	from coworks import TechMicroService
	from coworks import entry

	class SimpleExampleMicroservice(TechMicroService):

        @entry(content_type='text/html')
        def get_hi(self, lang='fr'):
            if lang=='fr':
                return "<p>bonjour</p>"
            return "<p>hello</p>"

If you return a tuple this default value is not set.

Binary type
^^^^^^^^^^^

.. code-block:: python

	from coworks import TechMicroService
	from coworks import entry

	class SimpleExampleMicroservice(TechMicroService):

        @entry(binary=True)
        def get_content_type(self):
            return b"test"

Nevertheless the current AWS ApiGateway integration with Lambda doesn't allow to defined the content type in response
header so the caller must know in advance the returned content type ot the entry.
Microservice Response
---------------------

``Flask`` automatically converts return values from a class microservice into a response
object for you.

* If the return value is a ``string`` or ``bytes``, it’s converted into a response object with the string or bytes
  list as response body, a 200 OK status code and a ``application/json`` mimetype.
* If the return value is a ``dict`` or a ``list``, it's converted to a JSON structure, a 200 OK status code and
  a ``application/json`` mimetype.
* If a ``tuple`` is returned the items in the tuple can provide extra information. Such tuples have to be in the
  form (response, status), or (response, status, headers). The status value will override the status code and headers
  can be a list or dictionary of additional header values.

Nevertheless we strongly recommend to use only JSON structure (``str`` or ``dict``) and use werkzeug ``HttpException``
for return status code. This allows you to easily call your entry from another entry.

Binary response
---------------

You can return a binary response on a specific entry::

	@entry(binary=True)
	def get(self):
		return b"the image bytes"

For such entry the returned value must be a list of bytes.

Unfortunately it is not possible with AWS Lambda to dynamically set the returned content-type.
So the content-type value may be set by the ``Accept`` header parameter or by fixing it for the route.


.. _blueprint:

Blueprints
----------

Blueprints
^^^^^^^^^^

Coworks blueprints are used to add to your application more routes deriving from logical components.
Blueprints allow you to complete your microservices with transversal functionalities.

Blueprints are a part of Flask. To learn more about how Blueprints are implemented and used in Flask,
check out `Flask Blueprints <https://flask.palletsprojects.com/en/2.0.x/blueprints/>`_.

Blueprint Registration
**********************

Blueprints are defined similarly to microservice classes. However, they will instead
inherit from the coworks implementation of the ``Blueprint`` object.

Methods within the class should still be decorated with ``@entry``.

.. code-block:: python

	from coworks import Blueprint

	class Admin(Blueprint):

	  @entry
		def get_context(self):
			return self.current_request.to_dict()

This blueprint defines a new route ``context``. To add this route to your microservice, just register the
microservice, you'll need to register the blueprint:

.. code-block:: python

	app = SimpleExampleMicroservice()
	app.register_blueprint(Admin(), url_prefix="/admin")

The ``url_prefix`` parameter adds the prefix ``admin`` to the route ``context``.
Now the ``SimpleExampleMicroservice`` has a new route ``/admin/context``.

Predefined Blueprints
*********************

Admin
:::::

The admin blueprint adds the following routes:

``/route``

	List all the routes of the microservice with the signature extracted from its associated function
    (similar to the coworks ``route`` command).

``/context``

	Return the deployment context of the microservice.

Other routes added by the admin blueprint are as follows::

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
