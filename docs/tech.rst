.. _tech:

TechMicroservices
=================

Mail
^^^^^

The ``mail`` microservice is a SMTP mail service :

``/send``

	[POST] Send mail.

	- Params :
		- from_addr=None : Required
		- to_addrs=None : Required
		- subject=""
		- body=""
		- starttls=False




S3
^^

The S3 microservice allows bucket manipulation :

``/buckets``

	[GET] Return the list of buckets.

``/bucket/{bucket}``

	[GET] If the key is undefined, returns the list of objects in the bucket ``bucket``.
	Else returns the object defined by the key ``key`` in the bucket ``bucket``.

		Params :
			- key=None

	[PUT] Creates the bucket ``bucket``.

	[DELETE] If the key is undefined, deletes the bucket ``bucket``.
	Else deletes the object defined by the key ``key`` in the bucket ``bucket``.

		Params :
			- key=None

``/content/{bucket}``

	[GET] Returns the content of the bucket object defined by ``key`` in ``bucket``.

		Params :
			- key: Required

	[PUT] Create the object defined by ``key`` in ``bucket`` with ``body`` as content.

		Params :
			- key: Required
			- body:b'' : Content in bytes.
