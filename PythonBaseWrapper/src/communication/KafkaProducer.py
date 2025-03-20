#!/usr/bin/env python3
#
# Copyright 2021 Moritz Gütlein
# 
# This code was originally published under the Apache 2.0 License (http://www.apache.org/licenses/LICENSE-2.0) in 2021.
# In 2025, it has been relicensed under the MIT License (https://choosealicense.com/licenses/mit/) with the explicit permission of all copyright holders.
#
# 

from confluent_kafka import avro
import csv
from confluent_kafka.avro.serializer import SerializerError
import json

from AvroProducerConsumer import AvroProducerStrKey
from confluent_kafka import Producer
from struct import *
from confluent_kafka.admin import AdminClient, NewTopic


class KafkaProducer():

    def __init__(self, broker, registry, producerID, useAvro=True, schema="", schemaPath=""):
        self.producerID = producerID
        self.broker = broker
        self.registry = registry

        self.producerConf = {'bootstrap.servers': broker, 'schema.registry.url': registry, 'acks': '1',
                             'enable.idempotence': 'false',
                             'linger.ms': '0'}
        self.admin = AdminClient({'bootstrap.servers': broker})
        if (useAvro):
            if len(schema) > 0:
                self.producer = AvroProducerStrKey(self.producerConf, default_value_schema=schema)
            elif len(schemaPath) > 0:
                schema = avro.load(schemaPath)
                self.producer = AvroProducerStrKey(self.producerConf, default_value_schema=schema)
        else:

            self.producerConf = {'bootstrap.servers': broker, 'acks': '1', 'enable.idempotence': 'false',
                                 'linger.ms': '0'}
            self.producer = Producer(self.producerConf)

    getbinary = lambda x, n: format(x, 'b').zfill(n)

    def produce(self, topic, value, key="empty", timestamp=-1):
        # print("< < < preparing headers", flush=True)
        headers = {}
        headers["sender"] = self.producerID
        headers["time"] = pack('!q', timestamp)
        headers["epoch"] = pack('!i', 0)
        self.producer.produce(topic=topic, value=value, key=key, headers=headers)
        # print("< < < publishing to", topic, flush=True)
        # self.producer.produce(topic=topic, value=value, key=key)
        self.producer.flush()

    # return True if topic exists and False if not
    def topic_exists(self, topic):
        metadata = self.admin.list_topics()
        for t in iter(metadata.topics.values()):
            if t.topic == topic:
                return True
        return False

    def create_topics(self, topics):
        kafka_topics = []
        for topic in topics:
            print("creating:", topic)
            if not self.topic_exists(topic):
                kafka_topics.append(NewTopic(topic, 1, 1))
        topic_results = None
        if kafka_topics:
            topic_results = self.admin.create_topics(kafka_topics)
        return topic_results

    def delete_topics(self, topics):
        del_topics = self.admin.delete_topics(topics, operation_timeout=30)

        # Wait for operation to finish.
        for topic, f in del_topics.items():
            try:
                f.result()  # The result itself is None
                print("Topic {} deleted".format(topic))
            except Exception as e:
                print("Failed to delete topic {}: {}".format(topic, e))


