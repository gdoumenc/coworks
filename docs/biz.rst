.. _biz:

BizMS
=====

BizMicroservices are microservices obtained by composition of TechMicroservices. The composition is defined with the
`Airflow <https://github.com/apache/airflow>`_ plateform.

** TO BE COMPLETED **



Operators
---------

.. module:: coworks.operators

.. autoclass:: TechMicroServiceOperator
    :members:

.. autoclass:: BranchTechMicroServiceOperator
    :members:

.. autoclass:: AsyncTechServicePullOperator
    :members:


Sensors
-------

This sensor is defined to wait until an asynchronous call is finished.

.. module:: coworks.sensors

.. autofunction:: AsyncTechMicroServiceSensor
