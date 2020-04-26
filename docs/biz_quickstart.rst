.. _biz_quickstart:

BizMS Quickstart
=================

This page gives a quick and partial introduction to CoWorks business microservices.
You must have understand first how to deploy technical microservice :doc:`tech`.

A biz microservice is defined by a definition of states (in YAML):

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
            goto: "Send mail"
      - name: "Send mail"
        tech:
          service: "mail"
          post: "/send"
          body:
            from_addr: "test@test.com"
            to_addrs: ["test@test.com"]
            body: "Server is down!"

And define a biz microservice  which will be triggered with a reactor :

.. code-block:: python

	from coworks import TechMicroService

	class CheckServerMicroService(TechMicroService):

		def post(self, url=None):
			if url is None:
				raise BadRequestError("No URL given...")
			resp = requests.get(url)
			return resp.status_code

	check = CheckMicroService(app_name='check')

	fact = BizFactory('check-server')
	fact.create('check', Once(), data={'url': 'http://www.google.com'})


Deployment
----------

As for TechMicroservice, the BizMicroservice may be deployed by terraform and updated by coworks.

Consider the previous Step Function is already defined. To update te source just enter the command::

	(project) $ cws update


