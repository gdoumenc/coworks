.. _biz_quickstart:

BizMS Quickstart
=================

This page gives a quick and partial introduction to CoWorks Business Microservices.
You must have understand first how to deploy technical microservice :doc:`tech`.

MicroServiceProxy
-----------------

To compose technical microservices, proxy interfaces are defined to allow asynchronous calls and reintrant
entries.

Deployment
----------

As for ``TechMicroService``, the ``BizMicroService`` may be deployed by the terraform deployer command.

Consider the previous Step Function is already defined. To update te source just enter the command::

	(project) $ cws update


