.. figure:: ./img/coworks.png
  :height: 100px
  :alt: CoWorks Logo
  :target: https://coworks.readthedocs.io/en/latest/?badge=latest

=======
CoWorks
=======

.. image:: https://travis-ci.com/gdoumenc/coworks.svg?branch=master
  :target: https://travis-ci.com/gdoumenc/coworks
  :alt: Travis CI
.. image:: https://readthedocs.org/projects/coworks/badge/?version=latest
  :target: https://readthedocs.org/projects/coworks/badge/
  :alt: Documentation Status
.. image:: https://codecov.io/gh/gdoumenc/coworks/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/gdoumenc/coworks
  :alt: Documentation Status

CoWorks is an unified compositional microservices framework over AWS technologies and
based on the `Chalice <https://github.com/aws/chalice>`__ microframework.
The aim of this project, is to offer a very simplified experience of microservices over the awesome technologies of AWS.

Each atomic microservice (Tech Microservice) is a simple python class deployed on the serverless Lambda product and
composition of microservices (Biz Microservice) is performed over the Step Function product. Other AWS products are used
for logging, administrate, ...

Get started with `installation <https://coworks.readthedocs.io/en/latest/installation.html>`_ and then
get an overview with the `quickstart <https://coworks.readthedocs.io/en/latest/quickstart.html>`_.
Read `faq <https://coworks.readthedocs.io/en/latest/faq.html>`_ for a quick presentation,
a complete presentation can be found `here <https://coworks.readthedocs.io/en/latest/>`_.


Contributing
------------

If you want to contribute to this project and make it better, your help is very welcome.

Just delete the microservice with ::

	$ chalice delete

Related Projects
----------------

* `Chalice <https://github.com/aws/chalice>`__ - Python Serverless Microframework for AWS.


