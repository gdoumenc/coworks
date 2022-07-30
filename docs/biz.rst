.. _biz:

BizMS
=====

BizMicroService is the orchestration of TechMicroServices. This orchestration is defined with the
`Airflow <https://github.com/apache/airflow>`_ plateform.

**Notice** : We recomand to create first a directory service as described in the directory :ref:`samples`.


DAG
---

The definition of the DAG, the BizMicroService, is done by thru ``biz`` decorator, which is simply a renaming
of the ``dag`` decorator of Airflow.

*Notice* : It seems stupid to just rename a decorator, but we have in mind to use this decorator in future for
creating relation dependencies between microservices.

.. code-block:: python

    from coworks.biz import biz

    DEFAULT_ARGS = {
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'email': "gdoumenc@neorezo.io",
        'email_on_failure': True,
        'email_on_retry': False,
    }


    @biz(
        default_args=DEFAULT_ARGS,
        tags=['coworks', 'sample'],
        start_date=datetime(2022, 1, 1),
        schedule_interval=None,
        catchup=False,
        render_template_as_native_obj=True,
    )
    def my_first_biz(data):
        ...

Operators
---------

TechMicroServiceOperator
^^^^^^^^^^^^^^^^^^^^^^^^

This first operator is for calling a TechMicroService.

.. code-block:: python

    create_invoice = TechMicroServiceOperator(
        task_id='create_invoice',
        cws_name='neorezo-billing_invoice-eshop',
        method='POST',
        entry="/invoice",
        json="{{ dag_run.conf['data'] }}",
    )

The arguments are :

 * ``cws_name`` : allows to call the microservice by its name thanks to the directory service,
 * ``method`` and ``entry`` : route to the service,
 * ``data`` or ``json`` :service parameters for ``GET`` and ``POST`` method respectively.


Other main arguments are needed to be understood :

 * ``directory_conn_id``: the airflow connection id used to call the directory microservice. By default 'coworks_directory'.
 * ``asynchronous``: Asynchronous status. By default 'False'.

``cws_name``, ``entry``, ``data``, ``json``, ``asynchronous`` arguments are templated.

If you don't want to use the directory microservice:

.. code-block:: python

    create_invoice = TechMicroServiceOperator(
        task_id='create_invoice',
        api_id='xxxxx',
        stage='v1',
        token='yyyy',
        method='POST',
        entry="/invoice",
        json="{{ dag_run.conf['data'] }}",
    )

BranchTechMicroServiceOperator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This branching operator allows to test microservice status code or result content


.. code-block:: python

    check_invoice = BranchTechMicroServiceOperator(
        task_id='check_invoice',
        cws_task_id='neorezo-billing_invoice-eshop',
        on_success = "sent_to_customer"
        on_failure = "mail_error"
    )

The arguments are :

 * ``cws_task_id`` : calling task id used to retrieve XCOM values,
 * ``on_success`` : branch task id on success,
 * ``on_failure`` :branch task id on failure.


Sensors
-------

This sensor is defined to wait until an asynchronous call is finished.

