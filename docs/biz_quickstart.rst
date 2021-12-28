.. _biz_quickstart:

BizMS Quickstart
=================

This page gives a quick and partial introduction to CoWorks Business Microservices.
You must have understand first how to deploy technical microservice :doc:`tech`.

Aiflow
------

The `Airflow <https://github.com/apache/airflow>`_ plateform is the core tool to implement the businness model.
Few concepts are needed to understand how ``BizMicroService`` works.

A ``BizMicroService`` is defined from an airflow DAG. It allows to trigger it manually or get running information from
it. Contrary to ``TechMicroService``, ``BizMicroService`` have states.

To interact with DAG defined in airflow, two main operators have been defined : ``TechMicroServiceOperator`` and
``BranchTechMicroServiceOperator``.

The first operator allows to call a technical microservice. The second one is a branching operator on the status
returned by a technical microservice..

At last, but not a least, the call to a microservice may be call **asynchronously**.
The called microservice stores automatically its result in
a S3 file, and a ``Sensor`` on this S3 file is then created to allow resynchronisation.