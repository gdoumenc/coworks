.. _biz_quickstart:

BizMicroService Quickstart
==========================

This page gives a quick and partial introduction to CoWorks Business Microservices.

*Beware* : you must have understand first how to deploy technical microservice :doc:`tech`.

Airflow
-------

The `Apache Airflow <https://github.com/apache/airflow>`_ plateform is the core tool to implement the business model.
As Flask for TechMicroService, the knowledge of Airflow is needed to fully understand the BizMicroService concept and
benefits.

Few concepts are needed to understand how ``BizMicroService`` works.

A ``BizMicroService`` is defined as an airflow DAG. It allows to trigger it manually or get running information from
it. Contrary to ``TechMicroService``, ``BizMicroService`` have states.

To interact with DAG defined in airflow, two main operators have been defined : ``TechMicroServiceOperator`` and
``BranchTechMicroServiceOperator``.
The first operator allows to call a technical microservice. The second one is a branching operator on the status
returned by a technical microservice.

At last, but certainly the more usefull and powerfull, the call to a microservice may be call **asynchronously**.
The called microservice stores automatically its result in
a S3 file, and a ``Sensor`` on this S3 file is then created to allow resynchronisation.
This asynchronous call is defined by an airflow task group : ``TechMicroServiceAsyncGroup``.

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
        start_date=datetime(2022, 1, 1),
        schedule_interval='@daily',
        catchup=False,
        render_template_as_native_obj=True,
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


You microservice is called every 5 minutes and traces are print in logs.
