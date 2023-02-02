.. _samples:

Samples
========

Impatient developers often love samples to learn quickly. In this part, we will show you how to use CoWorks to :

* Understand the CoWorks layer service.
* Create a directory service to call technical microservice by there name.
* Create a website with content defined in the CosmisJS headless tool.

.. _layers:

CoWorks layers
--------------

Very simple microservice defining a simple HTML page and a call thru javascript.

.. literalinclude:: ../samples/layers/tech/app.py

.. _headless:

Website
-------

Very simple microservice defining a simple HTML website.

.. literalinclude:: ../samples/website/tech/website.py

.. _directory:

Directory
---------

This microservice is usefull for the ``BizMicroservice``.

.. literalinclude:: ../samples/directory/tech/app.py

To create your directory service, you just have to define a file ``env_vars/vars.secret.json`` like ::

    {
      "AWS_USER_ACCESS_KEY_ID": XXXX,
      "AWS_USER_SECRET_ACCESS_KEY": YYY
    }

