.. _faq:

FAQ
===

This is a list of Frequently Asked Questions about ``CoWorks``.  Feel free to
suggest new entries!

Is CoWorks ...
--------------

... a complete unified approach?
	The hardest part of using the microservice approach is to be able to control, deploy, maintain and debug composition
	of many microservices. Having a compositional approach is the key for production usage.
	CoWorks integrates all information and convention to simplify such composition.
... independant of any specific IaaS?
	No, it relies only on AWS solutions. There are already performant solutions to abstract any cloud providers such as
	`Zappa <https://github.com/Miserlou/Zappa>`_, `Serverless <https://serverless.com/>`_...
	The aim of the ``CoWorks`` project is to simplify the experience of using microservices in production with AWS technologies
	not to provide a new model.
... complicated?
	No, the ``CoWorks`` framework is based on twos kinds of services:

	* Simple atomic microservices called ``TechMicroservices``.
	* Composed microservices called ``BizMicroservices``.

	The model uses mainly Lambda and Airflow technologies but those complex but awesome technologies are used
	in asimplified manner for users.

We welcome any contributions that improve the quality of our projects.


