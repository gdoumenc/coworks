.. _middleware:

Middleware
==========

Same as for `Werkzeug <https://werkzeug.palletsprojects.com/middleware>`_, you can define midleware to wrap the
microservice in order to observe or change its behavior.

Profiler
--------

You can use Werkzeug `ProfilerMiddleware <https://werkzeug.palletsprojects.com/en/2.0.x/middleware/profiler>`_
to profile each request.

This middleware can be associated to the predefined ``Profiler`` blueprint which define and entry to get
last request profile.

XRay
----

The predefined ``XRayMiddleware`` will create a tracking context where all informations
of the microservice execution will be logged on AWS XRay.

To use it :

.. code-block:: python

    from aws_xray_sdk.core import xray_recorder

    ...

    myservice = ...
    XRayMiddleware(myservice, xray_recorder)


When the microservice is in debug mode, the manager is replaced by a mock manager. You can also disable this context
manager by setting an environment variable :

.. code-block:: python

    AWS_XRAY_SDK_ENABLED = false


