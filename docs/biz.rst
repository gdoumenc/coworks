.. _Biz:

BizMicroservices
================

BizMicroservices are microservices obtained by composition of TechMicroservices. The composition is defined over the
AWS Step Function technology.

As we have seen a BizMicroservice is mainly connected to an event source for producting a functional reaction.

YAML Description
****************

We prefer YAML to JSON for structure description and we defined some conventino so we use ``cws`` to produce the JSON
Step Function description from our YAML CoWorks description.

YAML CoWorks descriptior is not as powerfull as JSON Step Function descriptor; it is a simplified subset for TehMicroservices
composition.

