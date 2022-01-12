.. _tech:

TechMS
======

TechMicroservices are the 'atoms' of the Coworks microservices framework. They represent the building blocks
for other more complex microservices.

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

This is usefull for offering a CRUD microservice:

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

You can type your URI parameters or data query to get them typed as native build-in type and not only string.

.. code-block:: python

	@entry
	def get(self, id:int):
		return f"the type of id is {type(id)}"

	@entry
	def get_(self, id:int = None):
		return f"the type of id is {type(id)}"


Query or body parameters
^^^^^^^^^^^^^^^^^^^^^^^^

You can define default parameters to your entrypoint function.
In that case the value of those default parameters are defined by query parameters or JSON body content.

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

*Beware*: With `API gateway` you can only use query parameters for a GET method, and body
parameters with a GET method will raise an error in execution.

You can also use the ``**`` notation to get any values::

	@entry
	def get_content(self, **kwargs):
		return f"here are all the parameters: {kwargs}"

**Note**: The current implementation doesn't take into account the typing of the entrypoint function parameters
(forcasted in a future release).
So all query parameters are from type ``string``. If you want to pass typed or structured values, use the JSON mode.

Microservice Response
---------------------

As for ``Flask``, the return value from a class microservice is automatically converted into a response
object for you.

* If the return value is a ``string`` or ``bytes``, it’s converted into a response object with the string or bytes
  list as response body, a 200 OK status code and a ``application/json`` mimetype.
* If the return value is a ``dict`` or a ``list``, it's converted to a JSON structure, a 200 OK status code and
  a ``application/json`` mimetype.
* If a ``tuple`` is returned the items in the tuple can provide extra information. Such tuples have to be in the
  form (response, status), or (response, status, headers). The status value will override the status code and headers
  can be a list or dictionary of additional header values.

Nevertheless we strongly recommand to use only JSON structure (``str`` or ``dict``) and use werkzeug ``HttpException``
for return status code. Then you can easily call your entry from another entry.

Binary response
---------------

You can return a binary response on a specifiy entry::

	@entry(binary=True)
	def get(self):
		return b"the image bytes"

For such entry the returned value must be a list of bytes.

Unfortunatly it is not possible with the Lambda to set dynamicaly the returned content-type.
So the content-type value may be set by the ``Accept`` header parameter or by fixing it for the route.


.. _blueprint:

Blueprints
----------

Blueprints
^^^^^^^^^^

Coworks blueprints are used to add to your application more routes deriving from logical components.
Blueprints allow you to complete your microservices with transversal functionalities.

Blueprint Registration
**********************

Blueprints are defined in the same way as microservice classes.

.. code-block:: python

	from coworks import Blueprint

	class Admin(Blueprint):

	    @entry
		def get_context(self):
			return self.current_request.to_dict()

This blueprint defines a new route ``context``. To add this route to your microservice, just register the
blueprint to the microservice.

.. code-block:: python

	app = SimpleExampleMicroservice()
	app.register_blueprint(Admin(), url_prefix="/admin")

The ``url_prefix`` parameter adds the prefix ``admin`` to the route ``context``.
Now the ``SimpleExampleMicroservice`` has a new route ``/admin/context``.

Predefined Blueprints
*********************

Admin
:::::

The admin blueprint adds the following routes :

``/route``

	List all the routes of the microservice with the signature extracted from its associated function
    (similar to the coworks ``route`` command).

``/context``

	Return the deployment context of the microservice.

