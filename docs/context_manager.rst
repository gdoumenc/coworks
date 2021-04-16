.. _context_manager:

Context Manager
===============

Same as for python, you can define a context manager to create a context to be established when executing the
microservice.

XRay
----

The predefiend context manager ``XRayContextManager`` will create a tracking context where all informations
of the microservice execution will be tracked on AWS XRay.

To use it :

.. code-block:: python

    from aws_xray_sdk.core import xray_recorder

    ...

    myservice = ...
    XRayContextManager(myservice, xray_recorder)


When the microservice is in debug mode, the manager is replaced by a mock manager. You can also disable this context
manager by setting an environment variable :

.. code-block:: python

    AWS_XRAY_SDK_ENABLED = false

