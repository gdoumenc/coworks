.. figure:: ./img/snowflake-coworks.png
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
* At least :ref:`faq` if not enough...

Using and derived from `Chalice <https://github.com/aws/chalice>`_ and ideas from `Flask-Classy <https://github.com/apiguy/flask-classy/>`_.

What does microservice means in CoWorks?
****************************************

In short, the microservice architectural style is an approach to developing a single application as a suite of small services,
each running in its own process and communicating with lightweight mechanisms.

In Microservice Architecture, authors M. Amundsen, I. Nadareishvili, R. Mitra, and M. McLarty add detail to the definition
by outlining traits microservice applications share:

* Small in size
* Messaging enabled
* Bounded by contexts
* Autonomously developed
* Independently deployable
* Decentralized
* Built and released with automated processes

In CoWorks, microservices are serverless services over RestFULL resource APIs.

Small in size
  Simply implemented as a python class.

Messaging enabled
  HTTP request-response with AWS API Gateway and lightweight messaging with AWS SQS.

Service oriented
  Technological service on Lambda and Functional service over Step Function.

Independently deployable
  A single command line to deploy.

Decentralized
  Serverless components.

Smart endpoints
  Deriving directly from class methods.

Two levels of microservice
**************************

In ``CoWorks`` microservices are divided in two categories :

**Small technical microservice**

  Implemented as a simple AWS lambda function, this kind of microservice a dedicated to technical
  operations over a specific service.

  Here are some examples of predefined technical services in CoWorks :

    * Mail
    * Jinja templating
    * Odoo

**Functional business microservice**

  Implemented over AWS Step Function, this kind of microservice allows non programmer to construct
  functional business workflows.

  Here are some examples of predefined business services in CoWorks :

    * Alert
    * Reminder

Distinction between TechMicroservice and BizMicroservice is not only the granularity size but also:

* TechMicroservice should be use only as receivers of orders coming from BizMicroservices.
* A BizMicroservice represents a logical workflow of actions while a MicroService represents a simple concrete action.
* A ThechMicroservice is an independant microservice while a BizMicroservice is connected to event handler (cron, notification, event, ..).
* A ThecMicroservice is more a handler pattern and BizMicroservice a reactor pattern.



User’s Guide
============

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
  faq
  changelog


Taking part in the project
==========================

If you want to contribute to this project in any kind, your help will be very welcome.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
