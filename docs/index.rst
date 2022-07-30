.. figure:: ./img/coworks.png
  :height: 100px
  :alt: Coworks Logo
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest

|Maintenance| |Build Status| |Documentation Status| |Coverage| |Python versions| |Licence|

.. |Maintenance| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=plastic
    :alt: Maintenance
.. |Build Status| image:: https://img.shields.io/travis/com/gdoumenc/coworks?style=plastic
    :alt: Build Status
.. |Documentation Status| image:: https://readthedocs.org/projects/coworks/badge/?version=master&style=plastic
    :alt: Documentation Status
.. |Coverage| image:: https://img.shields.io/codecov/c/github/gdoumenc/coworks?style=plastic
    :alt: Codecov
.. |Python versions| image:: https://img.shields.io/pypi/pyversions/coworks?style=plastic
    :alt: Python Versions
.. |Licence| image:: https://img.shields.io/github/license/gdoumenc/coworks?style=plastic
    :alt: Licence

Introduction
============

CoWorks is a unified serverless microservices framework based on AWS technologies
(`API Gateway <https://aws.amazon.com/api-gateway/>`_, `AWS Lambda <https://aws.amazon.com/lambda/>`_),
the `Flask <https://github.com/pallets/flask>`_ framework and the `Airflow <https://github.com/apache/airflow>`_
plateform.

Each atomic microservice (defined as ``class TechMicroService``) is a simple python class deployed as a serverless
AWS Lambda and can be called synchronously and asynchrously.

Composition of microservices (defined as ``class BizMicroService``) is performed over the tech microservices and
constructed by Airflow workflows.

Technical documentation :

* Get started: :ref:`installation`.
* Quick overview: :ref:`tech_quickstart` then :ref:`biz_quickstart`.
* The Command Line Interface :ref:`cli`.
* Full documentation: :ref:`doc`.
* At least :ref:`faq` if not enough...

Using and derived from `Flask <https://github.com/pallets/flask>`_
(`Donate to Pallets <https://palletsprojects.com/donate>`_).
Main other tools used:

* `Click <https://github.com/pallets/click>`_ - Command Line Interface Creation Kit.
* `Terraform <https://github.com/hashicorp/terraform>`_ - Infrastructure Configuration Management Tool.

Other AWS or Terraform technologies are used for logging, administration, …

What does microservice mean in CoWorks?
---------------------------------------

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
  All needed deployment information defined in the python class.

Decentralized
  Serverless components.

Smart endpoints
  Deriving directly from class methods.


What are CoWorks main benefits?
-------------------------------

Two levels of microservice
**************************

CoWorks microservices are divided in two categories :

**Small technical microservice**

  Implemented as a simple AWS Lambda function, this kind of microservice is dedicated to technical
  operations over a specific service. Technical miscroservice should be stateless.


**Functional business microservice**

  Implemented by Airflow workflow, this kind of microservice allows non programmer to construct
  functional business workflows.


Distinction between ``TechMicroservice`` and ``BizMicroservice`` is based not only on granularity size but also:

* A ``TechMicroservice`` should only be used as receivers of orders coming from ``BizMicroservices``.
* A ``BizMicroservice`` represents a logical workflow of actions while a ``TechMicroservice`` represents a simple
concrete action.
* A ``TechMicroservice`` is an independant microservice while a ``BizMicroservice`` is connected to event handlers
(cron, notification, event, ...).
* A ``TechMicroservice`` is more a handler pattern and ``BizMicroservice`` a reactor pattern.

Code oriented tools
*******************

Like any model of software architecture, it is very usefull to have complementary tools for programming, testing,
documenting or deploying over it.

The main advantage of using CoWorks is its ability to defined those tools, called `commands`, directly in
the microservice code.
Predefined commands like ``run`` (defined by the Flask framework) or ``deploy`` are provided,
but you can redefined them or creates new ones like for documentation or testing.

For more details, see: :ref:`command`.

Microservice architecture structuration
***************************************

The CoWorks microservice architecture provides some best pratices for code organization and directory structure.
Indeed it's so easy to start in serverless project, it's also easy to start moving the wrong direction.

**API and Lambda organization**

  With AWS API a single Lambda function handles a single HTTP verb/path combinaison. For Rest API it is better to have
  a single lambda function to handle all HTTP verbs for a particular resource.

  CoWorks regroups all microservice entrypoints into one single class. And a class is the resource granularity
  for the API.

  For example, following the CRUD design :

  .. figure:: ./img/resource_oriented.png
    :width: 800px

  The significant benefit of this architecture is that the number of Lambda functions is drastically reduced over a
  one to one CRUD event mapping.

**Configuration**

  CoWorks differenciates two kind of configurations:

    * Automation and command configuraton
    * Execution configuration

  For those who are familiar with the Twelve-Factor App methodology, the CoWorks configuration model correspond exactly
  with the strict separation of config from code. More precisely:

    * The project configuration file : *Use a declarative format for setup automation, to minimize time and cost for new developers joining the project*
    * The environmant variables file : *Env vars are easy to change between deploys without changing any code*

.. _doc:

Documentation
-------------

.. toctree::
  :maxdepth: 2
  :caption: Contents:

  installation
  tech_quickstart
  tech
  command
  configuration
  middleware
  biz_quickstart
  biz
  samples
  api
  faq
  contributing
  changelog


Taking part in the project
--------------------------

If you want to contribute to this project in any kind, your help will be very welcome.
Don't hesitate to contact any project's member.


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
