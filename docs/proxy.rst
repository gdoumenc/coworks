.. _context_manager:

Proxy
=====

From a ``TechMicroservice``, it is easy to create a proxy python class to interact with a deployed service.

This proxy class will be obtained as a result of the entry ``proxy`` of the ``admin`` blueprint.

Synchronous proxy
-----------------

A synchronous proxy is derived from the ``MicroServiceProxy`` class.

As services are deployed on AWS APIGateway, the target service is defined by 3 environment variables :

.. code-block:: python

        'CWS_ID' # AWS APIGateway id
        'CWS_TOKEN' # Coworks token in authorization function
        'CWS_STAGE' "# Deployment stage

Those variables may also be defined on a dict like object, allowing Flask or Django configuration to be used.

A proxy has mainly two main methods ``get`` and  ``post`` to retrieves usual entries.

To use it :

.. code-block:: python

    CONFIG = {
        'TEST_CWS_ID': "abcdefghhij", # AWS APIGateway id
        'TEST_CWS_TOKEN': "mytoken",  # Coworks token in authorization function
        'TEST_CWS_STAGE': "dev",      # Deployment stage (here dev)
    }

    from coworks.proxy import MicroServiceProxy

    ...

    class TestProxy(MicroServiceProxy):

        def __init__(self):
            super().__init__('TEST', config=CONFIG)

    def test():
        with TestProxy() as p:
            value, status = p.get('/entry1')
            value, status = p.get('/entry2')

The ``post`` method has a ``sync`` parameter to allow Event invocation type when its value is ``False``.


Asynchronous proxy
------------------

An asynchronous proxy is derived from the ``AsyncMicroServiceProxy`` class. It is a subclass of synchronous proxy
and extends it whith the ``async_get`` method to allow asynchronous get calls.

To use it :

.. code-block:: python

    def test():
        async def a(proxy):
            value, status = await proxy.async_get('/entry1')
            print(f"a: async {value}: ")

        async def b(proxy):
            value, status = await proxy.async_get('/entry2')
            print(f"b: async {value}: ")

        async def a_b():
            async with AsyncTestProxy() as proxy:
                await asyncio.gather(a(proxy), b(proxy))

        asyncio.run(a_b())


As lambda functions are not handling several events in the same instance of lambda, when you call sevaral entries
of the same service, Lambda will allocate new instances of it to process the event. So depending of your provisionning
asynchronous calls may be less or more efficient.

The asynchronous proxies are mainly usefull in ``TechMicroService`` orchestration fo for ``BizMicroservice``.

