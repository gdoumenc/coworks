.. figure:: ./img/coworks.png
  :height: 100px
  :alt: CoWorks Logo
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest

Introduction
============

CoWorks is unified serverless microservices framework on AWS technologies.

Each atomic microservice (``class TechMicroService``) is a simple python class deployed as serverless Lambda AWS and
composition of microservices (``class BizMicroService``) is performed over the Step Function AWS product.

Other AWS technologies are used for logging, administrate, ...

Documentation
-------------

* Get started: :ref:`installation`.
* Quick overview: :ref:`tech_quickstart` then :ref:`biz_quickstart`.
* The Command Line Interface :ref:`cli`.
* At least :ref:`faq` if not enough...

Using and derived from `Chalice <https://github.com/aws/chalice>`_ and some ideas from
`Flask-Classy <https://github.com/apiguy/flask-classy/>`_.

Other tools used:

* `Terraform <https://github.com/hashicorp/terraform>`_ - Infrastructure configuration management tool.
* `SCons <https://github.com/SCons/scons>`_ -  A software construction tool.


What does microservice means in CoWorks?
****************************************

In short, the microservice architectural style is an approach to developing a single application as a suite of small services,
each running in its own process and communicating with lightweight mechanisms.

In Microservice Architecture (Aligning Principles, Practices, and Culture),
authors M. Amundsen, I. Nadareishvili, R. Mitra, and M. McLarty add detail to the definition
by outlining traits microservice applications share:

* Small in size
* Messaging enabled
* Bounded by contexts
* Autonomously developed
* Independently deployable
* Decentralized
* Built and released with automated processes

In CoWorks, microservices are serverless services over APIs.

Small in size
  Simply implemented as a python class.

Messaging enabled
  API Gateway request-response managed services.

Service oriented
  Technological service on Lambda and Functional service over Step Function.

Independently deployable
  All needed deployement information defined in the python class.

Decentralized
  Serverless components.

Smart endpoints
  Deriving directly from class methods.

Two levels of microservice
**************************

In ``CoWorks`` microservices are divided in two categories :

**Small technical microservice**

  Implemented as a simple AWS Lambda function, this kind of microservice a dedicated to technical
  operations over a specific service.

  Here are some examples of technical services in CoWorks :

    * Mail
    * Jinja templating
    * Odoo

**Functional business microservice**

  Implemented over AWS Step Function, this kind of microservice allows non programmer to construct
  functional business workflows.

  Here are some examples of business services in CoWorks :

    * Invoicing Process
    * Automated Dashbords

Distinction between TechMicroservice and BizMicroservice is based not only on granularity size but also:

* TechMicroservice should be use only as receivers of orders coming from BizMicroservices.
* A BizMicroservice represents a logical workflow of actions while a MicroService represents a simple concrete action.
* A ThechMicroservice is an independant microservice while a BizMicroservice is connected to event handler (cron, notification, event, ..).
* A ThecMicroservice is more a handler pattern and BizMicroservice a reactor pattern.



Documentation
=============

.. toctree::
  :maxdepth: 2
  :caption: Contents:

  installation
  tech_quickstart
  tech
  tech_deployment
  biz_quickstart
  biz
  biz_deployment
  cli
  faq
  api
  changelog


Taking part in the project
==========================

If you want to contribute to this project in any kind, your help will be very welcome.
Don't hesitate to contact any project's member.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
