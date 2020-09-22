.. image:: https://github.com/gdoumenc/coworks/raw/dev/docs/img/coworks.png
  :height: 80px
  :alt: Coworks Logo
  :target: https://coworks.readthedocs.io/en/latest

|

.. image:: https://travis-ci.com/gdoumenc/coworks.svg?branch=dev
  :target: https://travis-ci.com/gdoumenc/coworks
  :alt: Travis CI
.. image:: https://readthedocs.org/projects/coworks/badge/?version=dev
  :target: https://readthedocs.org/projects/coworks/
  :alt: Documentation Status
.. image:: https://codecov.io/gh/gdoumenc/coworks/branch/dev/graph/badge.svg
  :target: https://codecov.io/gh/gdoumenc/coworks
  :alt: Documentation Status

Coworks is an unified compositional microservices framework over AWS technologies and
based on the `Chalice <https://github.com/aws/chalice>`__ microframework.
The aim of this project, is to offer a very simplified experience of microservices over the awesome technologies of AWS.

Each atomic microservice (Tech Microservice) is a simple python class deployed as serverless Lambda and
composition of microservices (Biz Microservice) is performed over the Step Function product.

You can get a quickstart on `TechMicroService <https://coworks.readthedocs.io/en/latest/tech_quickstart.html>`_ then
continue with `BizMicroService <https://coworks.readthedocs.io/en/latest/biz_quickstart.html>`_


Documentation
-------------

* Get started: `Installation <https://coworks.readthedocs.io/en/latest/installation.html/>`_
* Complete reference guide: `Documentation <https://coworks.readthedocs.io/en/latest/>`_.
* Read `FAQ <https://coworks.readthedocs.io/en/latest/faq.html/>`_ for other informations.


Contributing
------------

We work hard to provide a high-quality and useful framework, and we greatly value
feedback and contributions from our community. Whether it's a new feature,
correction, or additional documentation, we welcome your pull requests. Please
submit any `issues <https://github.com/aws/coworks/issues>`__
or `pull requests <https://github.com/aws/coworks/pulls>`__ through GitHub.

Related Projects
----------------

* `Chalice <https://github.com/aws/chalice>`_ - Python Serverless Microframework for AWS.
* `Click <https://github.com/pallets/click>`_ -  A package for creating beautiful command line interfaces.
* `Terraform <https://github.com/hashicorp/terraform>`_ - Infrastructure configuration management tool.


