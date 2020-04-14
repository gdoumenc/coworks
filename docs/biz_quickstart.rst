.. _biz_quickstart:

BizMS Quickstart
=================

This page gives a quick and partial introduction to CoWorks business microservices.
You must have understand first how to deploy technical microservice :doc:`tech`.

A biz microservice is defined by a definition of state (in YAML):

.. code-block:: yaml

    comment: 'Test if the server is alive and send mail to users if not'
    states:
      - name: "Check server"
        tech:
          service: "check"
          get: "/check"
      - name: "On error"
        choices:
          - not:
              var: "$.check_server.result.statusCode"
              oper: "NumericEquals"
              value: 200
            goto: "Send mail to Eric"
      - name: "Send mail"
        tech:
          service: "mail"
          post: "/send"
          params:
            from_addr: "test@test.com"
            to_addrs: ["test@test.com"]
            body: "No more hello world!!"
            starttls: True

And define a reactor which will trigger the execution:

.. code-block:: python

	biz = BizFactory(app_name='biz')
	biz.create('check_server', 'check', Once())

Deployment
----------

As for TechMicroservice, the BizMicroservice may be deployed by terraform and updated by coworks.

Consider the previous Step Function is already defined. To update te source just enter the command::

	(project) $ cws update


