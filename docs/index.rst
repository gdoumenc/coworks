.. figure:: ./img/snowflake-coworks.png
  :height: 100px
  :alt: CoWorks Logo
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest

Introduction
============

CoWorks is unified serverless microservices framework on AWS tehcnologies.

Each atomic microservice (called TechMicroservice) is a simple python class deployed on the serverless Lambda product and
composition of microservices (called BizMicroservice) is performed as a serverless workflow over the Step Function product.
Other AWS products are used for logging, administrate, ...

Get started with :ref:`installation` and then get an overview with the :ref:`quickstart`.
Read :ref:`faq` for a quick presentation, a complete presentation can be found `here <https://coworks.readthedocs.io/en/latest/>`_.

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


User’s Guide
============

.. toctree::
  :maxdepth: 2
  :caption: Contents:

  installation
  quickstart
  tutorial
  staging
  authorization
  blueprint
  tech
  biz
  faq
  changelog


Taking part in the project
==========================

We welcome any contributions that improve the quality of our projects.

Submitting pull requests
************************

If you are unsure about how to create a pull request, this guide should get you on track.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
