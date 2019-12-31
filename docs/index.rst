.. figure:: ./img/snowflake-coworks.png
  :height: 100px
  :alt: CoWorks Logo
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest

Introduction
============

CoWorks is a Restful Microservice Framework on AWS based on Lambda, AWS Step Function and API Gateway products using Chalice microframework.

Each microservice is a small web application on the serverless Lambda product and offering restfull API interface
for use and a web dashboard for administration.

Get started with :ref:`installation` and then get an overview with the :ref:`quickstart`.

Using and derived from `Chalice <https://github.com/aws/chalice>`_ and ideas from `Flask-Classy <https://github.com/apiguy/flask-classy/>`_.

What does microservice means in coworks?
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

In coworks, microservices are serverless services over RestFULL resource APIs.

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

User’s Guide
============

.. toctree::
  :maxdepth: 2
  :caption: Contents:

  installation
  quickstart
  authorization




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
