.. _middleware:

Middleware
==========

Same for Django or werkzeug, you can define middleware to control any call.

XRay
----

The predefiend middleware ``XRayMiddleware`` will generate all informations needed to trace the microservice activation.

To use it :

.. code-block:: python

    from aws_xray_sdk.core import xray_recorder

    ...

    myservice = ...
    XRayMiddleware(myservice, xray_recorder)
