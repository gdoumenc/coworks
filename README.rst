.. image:: https://github.com/gdoumenc/coworks/raw/dev/docs/img/coworks.png
    :height: 80px
    :alt: Coworks Logo

|

|Maintenance yes| |Build status| |Documentation status| |Coverage rate| |Python versions| |GitHub license|

.. |Maintenance yes| image:: https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=plastic
   :target: https://GitHub.com/Naereen/StrapDown.js/graphs/commit-activity
.. |Build status| image:: https://img.shields.io/travis/com/gdoumenc/coworks?style=plastic
    :alt: Travis (.com)
.. |Documentation status| image:: https://img.shields.io/readthedocs/coworks?style=plastic
    :alt: Read the Docs
.. |Coverage rate| image:: https://img.shields.io/codecov/c/github/gdoumenc/coworks?style=plastic
    :alt: Codecov.. image:: https://codecov.io/gh/gdoumenc/coworks/branch/dev/graph/badge.svg
.. |Python versions| image:: https://img.shields.io/pypi/pyversions/coworks?style=plastic
    :alt: PyPI - Python Version
.. |GitHub license| image:: https://img.shields.io/github/license/gdoumenc/coworks?style=plastic
    :alt: GitHub

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


