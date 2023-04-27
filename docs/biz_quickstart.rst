.. _biz_quickstart:

Biz Quickstart
==============

This page gives a quick and partial introduction to CoWorks Business Microservices.

*Beware* : you must have understand first how to deploy technical microservice :doc:`tech`.

Airflow concepts defined
------------------------

The `Apache Airflow <https://github.com/apache/airflow>`_ plateform is the core tool to implement the business model.
As Flask for TechMicroService, the knowledge of Airflow is needed to fully understand the BizMicroService concept and
benefits.

Few concepts are needed to understand how ``BizMicroService`` works.

A ``BizMicroService`` is defined as an airflow DAG. It allows to trigger it manually or get running information from
it. Instead of ``TechMicroService`` which may be considered as stateless, ``BizMicroService`` are mainly stateful.
At last, but certainly the more usefull and powerfull feature, the call to a microservice may be done **asynchronously**.

To interact with DAG defined in airflow, two main operators have been defined : ``TechMicroServiceOperator`` and
``TechMicroServiceAsyncGroup``; more precisely the mast one is a group of tasks.
The first operator allows to call a technical microservice. The second one is a group of tasks to call the technical
microservice in an asynchronous way, waiting for the execution end and reading the result.

In the asynchronous call, the called microservice stores automatically its result in
a S3 file, and a ``Sensor`` on this S3 file is then created to allow resynchronisation.

Start
-----

To create your first simple business microservice, create a file ``simple.py`` with the following content::

    from datetime import datetime
    from datetime import timedelta

    from coworks.biz import TechMicroServiceAsyncGroup
    from coworks.biz import TechMicroServiceOperator
    from coworks.biz import biz

    DEFAULT_ARGS = {
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
        'email': "gdoumenc@neorezo.io",
        'email_on_failure': True,
        'email_on_retry': False,
    }


    # noinspection PyTypeChecker,PyArgumentList
    @biz(
        default_args=DEFAULT_ARGS,
        tags=['air-et-sante', 'send', 'orders'],
        start_date=datetime(2023, 1, 1),
        schedule_interval='@daily',
        catchup=False,
    )
    def first():
        simple = TechMicroServiceAsyncGroup(
            'simple',
            api_id="xxxx",
            stage="dev",
            token="token",
            method='GET',
            entry='/',
        )

        @task()
        def print_result():
            context = get_current_context()
            ti = context["ti"]
            result = ti.xcom_pull(task_ids='simple.read')
            print(result)

        simple >> print_result


    first = first()


You microservice is called every day and traces are print in logs.
